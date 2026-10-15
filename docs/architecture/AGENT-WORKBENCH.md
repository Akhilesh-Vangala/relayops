# Model-directed investigation and local operator workbench

October12,2026. User requests substantially deeper AI engineering and visible agent behavior. Implemented owned workflow relay-agent-1. Earlier single-request/scaffold-only statements describe the foundation, superseded for current coverage.

## Agent protocol

The graph begins with tenant/case/source version and task, not all source records. Each model round chooses up to four evidence tools or one standalone control submission. observe_system covers procurement/warehouse/billing/case_management; inspect_document covers invoice/delivery_note. record_hypotheses stores up to three strict supported/contradicted/uncertain claims with real unique citations; interpretations remain unverified. submit_plan requires observed citations from all four systems and both documents, public hypothesis memory, correct scope/version and the declared business contract.

Public policy errors return bounded tool feedback, at most twice total. Every evidence call counts against24, and identical calls against3. Unknown tools, fake citations, malformed usage/identity or hard bounds cannot create actions. No private grading reference is sent to the model. Approval/execution are not agent tools.

The live controller has dynamic conditional edges. ScriptedAgent is a separate adaptive integration client, not a learned model; it follows real observed replies and deliberately submits an invalid amount before correcting in the demo. Known diagnostic/single-request planner paths remain for comparison.

## Multimodal browser evidence

BrowserEvidence serves original synthetic source pages on an ephemeral loopback server. Browser network access is limited to its own origin/read-only page paths; selectors are strict semantic enums. No arbitrary URL, JavaScript evaluation, click, file upload or write tool is exposed. Source strings are HTML escaped; CSP blocks active source content. Captures include actual PNG bytes, SHA256, accessibility text and versioned public records. Source versions are checked around capture; mismatch rejects the observation.

Image blocks enter provider tool results. Context retains the latest two image blocks; earlier textual observations and image hashes remain, with original PNG artifacts durable. This is actual pixel input plumbing and image pruning, not demonstrated VLM accuracy, OCR, scanned-document parsing or general GUI navigation. Browser contexts are not OS sandboxes.

## Persistence and model receipts

AsyncSqliteSaver checkpoints plain JSON graph state: messages, evidence, hypotheses, counters, calls, activity and plan. Source/runtime/dependency/client/pricing/browser fingerprints must match explicit recovery. Changed versions are not migrated. Completed graphs can be inspected without a new call. An interrupted transition resumes with retained counters. Tests cover recovery with a fresh controller; full distributed recovery remains future work.

AgentModel uses official AsyncAnthropic typed SSE, checks active resolved model and input count, reserves estimated commitments before generation, requires message_stop, records complete typed usage and saves the exact result before graph checkpoint commit. Completed matching receipts are replayed without another generation. Unknown/changed receipts block replay;429haszeroautomaticgeneration retries. Actual reported cost overruns increase committed amounts; unexpected cache billing becomes unresolved. Prices/estimates are not invoices. One-run-local ledger; shared cross-run billing/identity is pending.

Limits:12rounds,24evidence calls,3identical requests,2corrections,2048output/request12000total,8000input/request64000cumulative,240active model seconds,60generation deadline,30SDKtimeout,2MBprovider body,$0.50estimated cumulative commitment. Cancellation/failure retains uncertain requests. Source observations consume separate bounded browser calls.

## Workbench and execution

Routes:/,/cases,/cases/{scenario},/runs,/runs/{id},/architecture. New runs admit a strict fixed scenario/mode/browser flag with required idempotency key, four-active-run bound and local host/origin/JSON checks. Live selection requires private configuration. Background tasks own local investigations; startup marks unfinished runs interrupted, no paid replay. This is a single-process/local service, not distributed durable workflow infrastructure.

Run pages show actual stored events, source screenshots, public memory, proposed actions, counterfactual checks and review. Reports bind a version digest, captured artifacts and runtime/source metadata. Server checks completed verified report, hashes, current fingerprints and exact requested version before immutable review. Operator approval then authorizes sandbox execution. Repeated requests use action receipts; actual final-state verification remains separate. No production financial operation or vendor message exists.

Individual OIDC/RBAC, Temporal/PostgreSQL, external connector idempotency, OS isolation and cloud operation are pending. Local access labels/testclient allowances must not be marketed as enterprise identity. App is loopback-bound; do not publish it as a secure multitenant service without implementing release boundaries.

## Evidence

47unit/integration tests pass;5transport tests use the actual SDK with mocked httpx2 HTTP/SSE, not fake objects alone.16real browser checks pass: six screenshots, tool choices/correction, immutable review, stale rejection, execution-before-review denial, duplicate-effect prevention, grounded no-write clarification, deep links, five pages across320–1440px, monochrome/no overflow/runtime errors. Known scripted matrix12/12assessments passes; no held-out/live model result.

Implementation:agent.py,agent_transport.py,browser.py,scripted_agent.py,web.py,benchmark.py. Tests:test_agent.py,test_agent_transport.py,test_web.py,browser_workbench.py plus retained foundation tests. Evidence:ignored artifacts/generated/agent-upgrade-001. Final source/commit association is recorded after publication of the local commit.
