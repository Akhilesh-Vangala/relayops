#!/usr/bin/env bash
set -euo pipefail
cluster_name="${RELAY_KIND_CLUSTER:-relayops-ci}"
token="kind-only-access-token-0000000000000000"
evidence_dir="artifacts/generated/kind-smoke"
mkdir -p "${evidence_dir}"
cleanup() {
  result_code=$?
  kubectl -n relayops get pods > "${evidence_dir}/pods.txt" 2>&1 || true
  if [[ $result_code != 0 ]]; then
    kubectl -n relayops get events --sort-by=.lastTimestamp > "${evidence_dir}/events.txt" 2>&1 || true
    kubectl -n relayops logs deployment/relayops-api --all-containers > "${evidence_dir}/api.log" 2>&1 || true
    kubectl -n relayops logs deployment/relayops-worker --all-containers > "${evidence_dir}/worker.log" 2>&1 || true
  fi
  if [[ -n "${forward_pid:-}" ]]; then kill "${forward_pid}" 2>/dev/null || true; fi
  kind delete cluster --name "${cluster_name}" >/dev/null 2>&1 || true
}
trap cleanup EXIT
kind create cluster --name "${cluster_name}" --wait 120s
docker build -f backend/docker/Dockerfile --target runtime -t relayops:kind .
kind load docker-image relayops:kind --name "${cluster_name}"
kubectl apply -k infrastructure/kubernetes/overlays/kind
kubectl -n relayops wait --for=condition=complete job/relayops-migrate --timeout=240s
kubectl -n relayops rollout status deployment/relayops-api --timeout=180s
kubectl -n relayops rollout status deployment/relayops-worker --timeout=180s
# Stop workers before admission; restarting API must preserve the queued payload.
kubectl -n relayops scale deployment/relayops-worker --replicas=0
kubectl -n relayops wait --for=delete pod -l app.kubernetes.io/component=worker --timeout=90s
forward() {
  kubectl -n relayops port-forward service/relayops-api 18081:80 > /tmp/relayops-kind-forward.log 2>&1 &
  forward_pid=$!
  for _ in $(seq 1 60); do
    if curl -fsS -H 'Host: localhost' http://127.0.0.1:18081/readyz >/dev/null 2>&1; then return; fi
    sleep .5
  done
  return 1
}
forward
unauthenticated=$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: localhost' http://127.0.0.1:18081/)
[[ "${unauthenticated}" == "401" ]]
response=$(curl -fsS -H 'Host: localhost' -H "Authorization: Bearer ${token}" \
  -H 'Content-Type: application/json' -H 'Idempotency-Key: kind-browser-001' \
  -d '{"case_id":"short-shipment","mode":"scripted","browser":true}' http://127.0.0.1:18081/api/runs)
job_id=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"${response}")
kill "${forward_pid}"
wait "${forward_pid}" 2>/dev/null || true
kubectl -n relayops rollout restart deployment/relayops-api
kubectl -n relayops rollout status deployment/relayops-api --timeout=180s
forward
queued=$(curl -fsS -H 'Host: localhost' -H "Authorization: Bearer ${token}" "http://127.0.0.1:18081/api/runs/${job_id}")
python3 -c 'import json,sys; assert json.load(sys.stdin)["status"]=="queued"' <<<"${queued}"
kubectl -n relayops scale deployment/relayops-worker --replicas=2
kubectl -n relayops rollout status deployment/relayops-worker --timeout=180s
for _ in $(seq 1 120); do
  job=$(curl -fsS -H 'Host: localhost' -H "Authorization: Bearer ${token}" "http://127.0.0.1:18081/api/runs/${job_id}")
  run_status=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' <<<"${job}")
  if [[ "${run_status}" == "completed" ]]; then break; fi
  if [[ "${run_status}" =~ ^(failed|interrupted)$ ]]; then echo "Investigation ${run_status}" >&2; exit 1; fi
  sleep .5
done
[[ "${run_status}" == "completed" ]]
python3 -c 'import json,sys; r=json.load(sys.stdin)["assessment"]; assert r["simulation"]["passed"]; assert r["tool_calls"]==6; assert all(e.get("browser") for e in r["evidence"])' <<<"${job}"
version=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["assessment"]["version"])' <<<"${job}")
printf '%s\n' "${job}" > "${evidence_dir}/assessment.json"
curl -fsS -H 'Host: localhost' -H "Authorization: Bearer ${token}" -H 'Content-Type: application/json' \
  -d "{\"version\":\"${version}\",\"action\":\"approve\"}" "http://127.0.0.1:18081/api/runs/${job_id}/review" > "${evidence_dir}/review.json"
for iteration in 1 2; do
  curl -fsS -H 'Host: localhost' -H "Authorization: Bearer ${token}" -H 'Content-Type: application/json' \
    -d "{\"version\":\"${version}\"}" "http://127.0.0.1:18081/api/runs/${job_id}/execute" > "${evidence_dir}/execution-${iteration}.json"
  python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["passed"] and r["checks"]["no_duplicate_effects"]' "${evidence_dir}/execution-${iteration}.json"
done
echo 'Kind: API restart preserved queue; six browser observations; verified simulation; exact review; no duplicate sandbox effects.'
