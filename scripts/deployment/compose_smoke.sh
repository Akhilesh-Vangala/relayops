#!/usr/bin/env bash
set -euo pipefail
export RELAY_ACCESS_TOKEN=compose-only-access-token-0000000000000000
export RELAY_POSTGRES_PASSWORD=composeOnlyPassword000
export RELAY_PORT=18100
export RELAY_PUBLIC_ORIGIN=""
project_name="relayops-ci-${RANDOM}"
evidence_dir="artifacts/generated/compose-smoke"
mkdir -p "${evidence_dir}"
cleanup() {
  scripts/deployment/compose.sh -p "${project_name}" logs --no-color > "${evidence_dir}/services.log" 2>&1 || true
  scripts/deployment/compose.sh -p "${project_name}" down --volumes --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT
scripts/deployment/compose.sh -p "${project_name}" config --quiet
scripts/deployment/compose.sh -p "${project_name}" up --build --wait --wait-timeout 240
python3 - <<'PY'
import json, os, time, urllib.request
from pathlib import Path
base='http://127.0.0.1:18100'
headers={'Authorization':'Bearer '+os.environ['RELAY_ACCESS_TOKEN'],'Content-Type':'application/json'}
def request(path, value=None):
    data=json.dumps(value).encode() if value is not None else None
    req=urllib.request.Request(base+path,data=data,headers={**headers,'Idempotency-Key':'compose-browser-001'})
    with urllib.request.urlopen(req,timeout=10) as response:
        return json.load(response)
assert request('/readyz')['status']=='ready'
identity=request('/api/runs',{'case_id':'short-shipment','mode':'scripted','browser':True})['id']
for _ in range(120):
    value=request('/api/runs/'+identity)
    if value['status']=='completed':break
    assert value['status'] not in ('failed','interrupted'),value['status']
    time.sleep(.5)
assert value['status']=='completed'
report=value['assessment']
assert report['simulation']['passed'] and report['tool_calls']==6
assert all(record.get('browser') for record in report['evidence'])
request('/api/runs/'+identity+'/review',{'version':report['version'],'action':'approve'})
for _ in range(2):
    result=request('/api/runs/'+identity+'/execute',{'version':report['version']})
    assert result['passed'] and result['checks']['no_duplicate_effects']
Path('artifacts/generated/compose-smoke/result.json').write_text(json.dumps({'passed':True,'browser_observations':6,'no_duplicate_effects':True,'live_model_generation':False},indent=2)+'\n')
print('Compose: independent API/worker/PostgreSQL, six browser observations, exact review and no duplicate sandbox effects.')
PY
