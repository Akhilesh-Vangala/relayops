## October21 — no-credit reliability and availability

Public SSE delivery now retains terminal results/errors separately from a bounded progress mailbox, coalesces cross-thread wakeups and ends with actionable failure after 25 seconds. Slow/disconnected consumers do not receive late reports. Tests inject progress floods, worker faults, deadline expiry and disconnects; a running read-only thread may finish and is not claimed killed.

Agent boundary corrections are verified without model requests: VerifyOps rejects missing/partial usage in both controllers and marks incomplete receipt accounting unknown; RelayOps rejects malformed usage, non-finite/negative elapsed time and invalid tool names; QueryPilot rejects duplicate/non-finite/oversized/nontext model JSON and preserves complete valid tool transcripts. These are protocol reliability tests, not model quality measurements.

A credential-free public monitor checks five real upload formats, exact domain results, SSE progress, report authenticity/tamper rejection, rejection boundaries, current script delivery and recorded-video ranges. Required import/browser CI executes the actual monitor against its isolated local app. A separate twice-hourly canonical workflow retains bounded evidence. [Availability, schedule limitations and recovery](../operations/AVAILABILITY.md). Keep the last ready Vercel deployment serving while previews and protected CI run. Current publication results must be observed and recorded; older dated histories remain preserved.

Remaining gates: genuine private provider credentials/budget, live held-out/cost/latency benchmarks, configured hosted identity, durable isolated monitored tenant operation and actual-user feedback. No public provider enablement, external business writes, new cloud services or paid model calls.

# October16 — bounded multi-format import

The product accepts CSV, TSV, Excel .xlsx, JSON and JSONL, with explicit worksheet selection, deterministic normalization and unchanged domain rules. New parser/domain equivalence and actual five-format browser journeys are part of required CI. [Import contract](../product/FILE-IMPORTS.md). Publication status must be verified through the protected PR and canonical source metadata; live inference, hosted Auth and monitored durable customer execution remain separate gates. Previous release notes below are preserved.

# October15 product workspace verification

Implemented and locally verified RelayOps product landing, guided own-data source/rules/results, real observed stages, explicit immutable device projects/history, backup restore and signed saved-report checks. 85 native tests, including actual PostgreSQL queue/recovery cases; 16 private-workbench browser checks; 12 grouped product checks and 14 axe views pass. Both actual owner-RLS/concurrent quota checks pass in disposable PostgreSQL. Recordings use current source and real browser pixels. Publication must use protected required CI and exact-source deployment verification; these local checks do not establish hosted Auth, live-model quality, real users or monitored durable operations. See [product implementation](../product/PRODUCT-WORKSPACE.md). Existing release gates and history below remain applicable.

# RelayOps progress and evidence

## October 15 — Repository organization and demo refresh

Implemented explicit frontend/backend ownership, a curated technical documentation index, current README/evidence scope and original actual browser recordings. Native regression suites pass; protected remote checks and post-promotion public verification are the publication gates for this increment. Current paths and source ownership are documented in [layout](../development/LAYOUT.md).

| Existing evidence baseline | Scope |
| --- | --- |
| [CI38662633663](https://github.com/Akhilesh-Vangala/relayops/actions/runs/38662633663) | Passed 65-case suite, known scripted assessments, private/public browser, Compose and Kind before this reorganization. |
| Public application | Synthetic reviewed actions and explicit uncertainty recovery. |
| New recording | Actual continuous Chromium capture and a separate six-frame GIF preview. [Provenance](../DEMO.md). |

Do not interpret the older source baseline as a test of new path changes. The required PR workflow verifies the new tree before merge; final publication evidence is linked in the merged PR and current Actions page.

No paid model calls or actual-user validation. Live-model quality and customer-production gates remain open.

[Full prior progress history](history/PRE-ORGANIZATION-PROGRESS.md).
