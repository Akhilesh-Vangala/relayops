> Historical record. [Current project overview](../../../README.md) and [current handoff](../HANDOFF.md) take precedence.

# End-to-end flow

October12 current implementation: [model-directed agent and local workbench](../../architecture/AGENT-WORKBENCH.md) add persistent dynamic tool selection, real browser/document screenshots, cited public hypotheses, bounded correction, actual SDK HTTP/SSE checks and operator pages. Earlier no-browser/no-server/single-call-only statements below describe the initial foundation and are superseded for current coverage; live quality, arbitrary UI actions, scanned-document extraction and distributed/cloud release remain pending.

1. Initialize a fresh original synthetic fixture.
2. Observe procurement, warehouse, billing and case management; register source-versioned evidence IDs.
3. Diagnostic or gated model returns a strict proposed Plan.
4. Policy validates tenant/case/version, exact observed citations, information requirements and permitted action sequence/amounts.
5. Clone the world into a private temporary fixture; replay exact public evidence and simulate approved effects on that copy only.
6. Independent evaluator checks output state, unchanged source facts, explicit review and absence of duplicate actions.
7. Original fixture remains unchanged unless CLI sandbox execution is explicitly requested.
8. Explicit approval binds the exact plan digest. Each sandbox action records its receipt and business effect transactionally.
9. Lost acknowledgement stops execution with an unknown receipt. Explicit reconciliation inspects state and confirms the effect without sending it again.
10. Resume confirmed receipts without duplicate effects; recheck source version before each next action; changed source requires fresh evidence/review. Save partial state rather than declare success.

This initial backend is a single SQLite fixture, so atomic receipt/effect transactions do not prove recovery across real independent external systems. Actual browser actions, cross-service reconciliation, durable orchestration and compensation remain pending.
