"use strict";
let config = null,
  selectedCase = "",
  activeTab = "result",
  busy = "",
  error = "";
const app = document.querySelector("#app");
const CACHE_KEY = "relayops-interactive-runs-v1";
const SYSTEMS = ["procurement", "warehouse", "billing", "case_management"];
const ACTIONS = {
  hold_invoice: "Hold disputed invoice amount",
  open_supplier_claim: "Open supplier shortage claim",
  reserve_replacement: "Reserve replacement stock",
  resolve_case: "Resolve the case",
};
const OUTCOMES = {
  "short-shipment": ["resolve", "Four scoped actions after review"],
  "unknown-delivery": ["needs information", "No action until delivery is confirmed"],
  "low-stock": ["needs information", "Replacement stock cannot cover the shortage"],
  "healthy-delivery": ["no change", "Source records stay untouched"],
};
const STAGES = [
  ["observe", "Observe", "Agent"],
  ["propose", "Propose", "Agent"],
  ["policy", "Policy", "Validator"],
  ["simulate", "Simulate", "Private copy"],
  ["review", "Review", "Operator"],
  ["execute", "Execute", "Action broker"],
];
const esc = (value) =>
  String(value == null ? "" : value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const json = (value) => `<pre>${esc(JSON.stringify(value, null, 2))}</pre>`;
const label = (value) => String(value).replaceAll("_", " ");
const money = (cents) =>
  (cents / 100).toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
  });

function records() {
  try {
    const value = JSON.parse(sessionStorage.getItem(CACHE_KEY) || "[]");
    return Array.isArray(value)
      ? value.filter(
          (r) => r && typeof r.id === "string" && typeof r.case_id === "string",
        )
      : [];
  } catch {
    return [];
  }
}
function save(run) {
  const value = { ...run, viewed_at: new Date().toISOString() };
  sessionStorage.setItem(
    CACHE_KEY,
    JSON.stringify(
      [value, ...records().filter((r) => r.id !== value.id)].slice(0, 12),
    ),
  );
  return value;
}
function current() {
  const id = location.pathname.split("/")[3];
  return records().find((r) => r.id === id);
}
function go(path) {
  history.pushState({}, "", path);
  activeTab = "result";
  error = "";
  render();
  window.scrollTo(0, 0);
}
async function post(action, body) {
  const response = await fetch("/api/demo/" + action, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("The request did not complete. Start a new investigation.");
  }
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "The submitted input was not accepted.",
    );
  return data;
}
async function perform(text, action, body, tab = "result") {
  busy = text;
  error = "";
  render();
  try {
    const run = save(await post(action, body));
    go("/demo/runs/" + run.id);
    activeTab = tab;
  } catch (e) {
    error = e.message;
  } finally {
    busy = "";
    render();
  }
}
function table(columns, rows, className = "") {
  if (!columns?.length) return "";
  return `<div class="table-wrap"><table class="${className}"><thead><tr>${columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${(rows || []).map((row) => `<tr>${row.map((v) => `<td>${v == null ? "—" : v}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
function status(state) {
  return `<span class="status status-${esc(state.replaceAll(" ", "-"))}">${esc(state)}</span>`;
}
function banner() {
  return `<div class="demo-note">Interactive synthetic sandbox · Guided investigator · No live model calls or external business effects</div>`;
}
function shell(content) {
  const path = location.pathname;
  const link = (href, text, active) =>
    `<a href="${href}" data-go="${href}" class="${active ? "active" : ""}">${text}</a>`;
  return `<div class="shell"><aside class="sidebar"><a class="brand" href="/demo" data-go="/demo"><span class="brand-mark">R</span>RelayOps</a><div class="sidebar-caption">OPERATIONS WORKSPACE</div><nav class="nav"><a href="/uploads">Use your own data ↗</a>${link("/demo", "New investigation", path === "/demo" && location.hash !== "#history")}${link("/demo#history", "Investigation history", location.hash === "#history" || path.startsWith("/demo/runs/"))}${link("/demo/architecture", "Architecture", path === "/demo/architecture")}${link("/demo/recording", "Watch recorded demo", path === "/demo/recording")}<a href="https://github.com/Akhilesh-Vangala/relayops" target="_blank" rel="noreferrer">Source on GitHub ↗</a></nav><p class="sidebar-note">Reports stay in this browser session. Download evidence to keep a copy.</p></aside><main class="workspace"><header class="topbar"><span>Workspace / ${path.includes("/runs/") ? "Investigation" : path === "/demo/architecture" ? "Architecture" : "Overview"}</span><span class="pill">Interactive demo</span></header>${banner()}${content}<footer class="footer">RelayOps · Original synthetic fixtures · Explicit verification and review</footer></main></div>`;
}
function statusUI() {
  return `${busy ? `<div class="progress" role="status">${esc(busy)}</div>` : ""}${error ? `<div class="error" role="alert">${esc(error)}</div>` : ""}`;
}
function home() {
  return `<div class="heading"><div class="eyebrow">EVIDENCE TO VERIFIED ACTION</div><h1>Resolve the exception.<br>Check every effect.</h1><p class="muted">Inspect an operational case, review a grounded proposal and execute the approved actions in an isolated sandbox.</p></div><div class="stats"><div><span>Runnable cases</span><strong>${config.cases.length.toString().padStart(2, "0")}</strong></div><div><span>Your investigations</span><strong>${records().length.toString().padStart(2, "0")}</strong></div><div><span>Execution</span><strong class="word">Isolated effects</strong></div></div><div class="grid"><section><div class="card"><h2>Start a working investigation</h2><form id="start-form"><label for="case">Choose a synthetic case</label><select id="case" ${busy ? "disabled" : ""}>${config.cases.map((c) => `<option value="${esc(c.id)}" ${c.id === selectedCase ? "selected" : ""}>${esc(c.title)}</option>`).join("")}</select><p class="muted">${esc(config.cases.find((c) => c.id === selectedCase)?.description)}</p><button ${busy ? "disabled" : ""}>${busy ? "Investigation running…" : "Investigate case ↗"}</button></form>${statusUI()}</div><div class="card"><div class="eyebrow">EXPLORE THE CASES</div><h2>Different outcomes, same controls.</h2><div class="case-list">${config.cases
    .map((c) => {
      const [outcome, note] = OUTCOMES[c.id] || ["", ""];
      return `<button class="case-option ${c.id === selectedCase ? "selected" : ""}" data-case="${esc(c.id)}" ${busy ? "disabled" : ""}><span class="case-head"><strong>${esc(c.title)}</strong>${outcome ? status(outcome) : ""}</span><span>${esc(c.description)}</span><small>${esc(note)}</small></button>`;
    })
    .join(
      "",
    )}</div></div></section><aside><div class="card"><div class="eyebrow">THE WORKING JOURNEY</div><h2>From discrepancy to verified resolution.</h2><ol class="flow">${[
    ["Observe", "Read procurement, warehouse, billing and case records."],
    ["Propose", "Validate the exact action amounts and source version."],
    ["Simulate", "Execute on a private fixture copy and independently check effects."],
    ["Review + act", "Approve, execute and inspect receipts. Test acknowledgment loss and reconciliation."],
  ]
    .map(([a, b]) => `<li><div><strong>${a}</strong><p>${b}</p></div></li>`)
    .join(
      "",
    )}</ol></div><div class="card"><h3>What runs on the server</h3><p class="muted">Each action calls the real planner, policy validator, counterfactual simulator, executor and independent evaluator against a freshly rebuilt fixture. The guided planner is deterministic and makes no model call.</p><a href="/demo/architecture" data-go="/demo/architecture">See the authority boundaries →</a></div></aside></div>`;
}
function historyPage() {
  return `<div class="heading"><div class="eyebrow">THIS BROWSER SESSION</div><h1>Investigation history</h1><p class="muted">Open a retained report, inspect its evidence or download a copy.</p></div><section class="card"><div class="section-heading"><h2>Your reports</h2><a class="button" href="/demo" data-go="/demo">New investigation ↗</a></div>${
    records().length
      ? records()
          .map(
            (r) =>
              `<a class="history-row" href="/demo/runs/${esc(r.id)}" data-go="/demo/runs/${esc(r.id)}"><div><strong>${esc(r.title)}</strong><small>${esc(new Date(r.viewed_at).toLocaleString())} · ${esc(r.id.slice(0, 8))}</small></div><span class="pill">${esc(r.stage)}</span></a>`,
          )
          .join("")
      : `<div class="empty">No investigations in this browser yet. Run a case to create a report.</div>`
  }</section>`;
}
function architecturePage() {
  const owners = [
    ["Observe", "Agent", "Read-only tools return one scoped system or document per call, each with a content-addressed evidence ID and source version."],
    ["Propose", "Agent", "A strict Pydantic plan cites at least four evidence IDs. Hypotheses must reference evidence observed in the same run."],
    ["Validate", "Policy", "Deterministic admission recomputes the shortage, required outcome and exact action amounts. Forged, stale or cross-tenant evidence is refused."],
    ["Simulate", "Simulator", "The plan executes on a private SQLite copy. Independent final-state checks run outside the agent's tool surface."],
    ["Review", "Operator", "Approval binds to the SHA-256 digest of the exact plan. A changed source or plan invalidates it."],
    ["Execute", "Action broker", "One action per transaction with a deterministic receipt ID. A confirmed receipt is skipped on retry."],
    ["Reconcile", "Action broker", "An unknown receipt blocks retry. Observed business state must prove the effect before the receipt is confirmed."],
  ];
  const limits = [
    ["Model rounds", "12"],
    ["Output tokens per investigation", "12,000"],
    ["Active model time", "240 s"],
    ["Evidence tool calls", "24"],
    ["Identical evidence calls", "3"],
    ["Public validation corrections", "2"],
    ["Tool calls per round", "4"],
    ["Input tokens per round", "8,000"],
    ["Cumulative estimated spend", "$0.50"],
    ["Images kept in model context", "2 most recent"],
    ["Worker lease / heartbeat", "60 s / 10 s"],
    ["Active queued runs", "16"],
  ];
  return `<div class="heading"><a class="back" href="/demo" data-go="/demo">← Workspace</a><div class="eyebrow">AUTHORITY BOUNDARIES</div><h1>The model observes and proposes.<br>Nothing else.</h1><p class="muted">Each stage is owned by a separate component. The agent cannot approve, execute, reconcile or read the evaluator.</p></div><section class="card"><h2>Who owns each step</h2><ol class="authority">${owners.map(([step, owner, text], i) => `<li><span class="authority-index">${String(i + 1).padStart(2, "0")}</span><div><div class="authority-head"><strong>${step}</strong><span class="owner owner-${owner.toLowerCase().replace(" ", "-")}">${owner}</span></div><p>${text}</p></div></li>`).join("")}</ol></section><div class="grid"><section class="card"><h2>Limits enforced in code</h2>${table(["Bound", "Value"], limits.map(([a, b]) => [esc(a), `<strong>${esc(b)}</strong>`]))}</section><aside><div class="card"><h3>Lost acknowledgment</h3><p class="muted">If an action's acknowledgment is lost, its receipt stays <em>unknown</em>. Retrying is refused. Reconciliation reads the billing and case state, confirms the receipt only if the effect matches, and then completes the remaining actions.</p></div><div class="card"><h3>Durable deployment</h3><p class="muted">Private deployments run the FastAPI API and separate leased investigation workers over PostgreSQL 17. Workers capture Playwright browser evidence and resume from LangGraph checkpoints. Kubernetes manifests ship with a Kind overlay.</p></div></aside></div>`;
}
function stepper(r) {
  const done = r.stage !== "rejected" && ["approved", "uncertain", "executed"].includes(r.stage);
  const noActions = !r.plan.actions.length;
  const state = {
    observe: "done",
    propose: "done",
    policy: "done",
    simulate: r.simulation.passed ? "done" : "failed",
    review: noActions ? "skipped" : r.stage === "rejected" ? "failed" : done ? "done" : "current",
    execute: noActions || r.stage === "rejected" ? "skipped" : r.stage === "executed" ? "done" : r.stage === "uncertain" ? "warning" : done ? "current" : "waiting",
  };
  return `<ol class="stepper" aria-label="Workflow progress">${STAGES.map(([id, name, owner]) => `<li class="step-${state[id]}"><span class="dot" aria-hidden="true"></span><div><strong>${name}</strong><small>${owner} · ${state[id]}</small></div></li>`).join("")}</ol>`;
}
function relayControls(r) {
  if (!r.plan.actions.length)
    return `<div class="callout">${r.plan.outcome === "needs_information" ? "Additional authoritative evidence is needed. No business actions were proposed." : "The case needs no business change. Source records are preserved."}</div>`;
  if (r.stage === "assessed")
    return `<div class="toolbar"><button data-action="approve" ${busy ? "disabled" : ""}>Approve sandbox proposal</button><button class="secondary" data-action="reject" ${busy ? "disabled" : ""}>Reject proposal</button></div>`;
  if (r.stage === "approved")
    return `<div class="review-summary">This exact proposal was approved in your sandbox branch.</div><div class="toolbar"><button data-action="execute" ${busy ? "disabled" : ""}>Execute approved actions</button><button class="secondary" data-action="lost-ack" ${busy ? "disabled" : ""}>Test lost acknowledgment</button></div>`;
  if (r.stage === "uncertain")
    return `<div class="callout notice"><strong>Acknowledgment uncertain.</strong> The hold may already have applied. Reconcile its observed state before continuing.</div><button data-action="reconcile" ${busy ? "disabled" : ""}>Reconcile and complete</button>`;
  return `<div class="review-summary">${r.stage === "executed" ? "Sandbox effects verified. Inspect the state diff, receipts and execution checks." : "Proposal rejected. This branch cannot execute actions."}</div>`;
}
function actionValue(a) {
  return a.kind === "hold_invoice"
    ? money(a.amount)
    : a.kind === "resolve_case"
      ? "Resolved"
      : a.amount + " units";
}
function result(r) {
  return `<div class="eyebrow">${r.stage === "executed" ? "EXECUTED SANDBOX RESULT" : "CHECKED PROPOSAL"}</div><h2>${r.stage === "executed" ? "The sandbox case is resolved and verified." : r.stage === "uncertain" ? "An action needs reconciliation." : r.plan.outcome === "resolve" ? "A scoped resolution is ready for review." : r.plan.outcome === "no_change" ? "No change is required." : "Clarification is required before acting."}</h2><p class="muted">${esc(r.plan.explanation)}</p><div class="steps-summary"><div><div class="state-label">Confirmed shortage</div><div class="effect-number">${r.before.procurement.ordered_units - r.before.warehouse.received_units} units</div></div><div><div class="state-label">Current sandbox hold</div><div class="effect-number">${money(r.after.billing.held_cents)}</div></div></div><h3>Proposed business actions</h3>${
    r.plan.actions.length
      ? table(
          ["#", "Action", "Amount"],
          r.plan.actions.map((a, i) => [i + 1, esc(ACTIONS[a.kind]), esc(actionValue(a))]),
        )
      : `<p class="muted">No business actions. The policy requires the outcome <strong>${esc(label(r.plan.outcome))}</strong>.</p>`
  }<h3>Explicit sandbox review</h3>${relayControls(r)}<div class="callout">Only this synthetic fixture can change. Request replay rebuilds an isolated simulation; it does not resend an external supplier or financial action.</div>`;
}
function formatField(field, value) {
  if (value === null || value === undefined) return "—";
  if (field.endsWith("_cents")) return money(value);
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}
function diffRows(r) {
  const rows = [];
  for (const system of SYSTEMS)
    for (const field of Object.keys(r.before[system] || {})) {
      const before = r.before[system][field],
        after = r.after[system]?.[field];
      rows.push({ system, field, before, after, changed: JSON.stringify(before) !== JSON.stringify(after) });
    }
  return rows;
}
function ledger(r) {
  const reconciled = new Set(
    r.events.filter((e) => e.kind === "reconciled").map((e) => e.payload.receipt),
  );
  return r.events
    .filter((e) => e.kind === "action_applied")
    .map((e, i) => {
      const final = r.receipts.find((x) => x.action_index === i)?.status || e.payload.status;
      const state = reconciled.has(e.payload.receipt) ? "reconciled" : final;
      return [
        i + 1,
        esc(ACTIONS[e.payload.kind]),
        esc(actionValue(e.payload)),
        `<code>${esc(e.payload.receipt.slice(0, 10))}</code>`,
        status(state),
      ];
    });
}
function effects(r) {
  const rows = diffRows(r),
    changed = rows.filter((x) => x.changed);
  const entries = ledger(r);
  return `<h2>State diff and receipts</h2><p class="muted">${changed.length} of ${rows.length} fixture fields changed. Every source field the policy reads stays identical.</p><div class="diff-summary">${SYSTEMS.map((s) => {
    const n = rows.filter((x) => x.system === s && x.changed).length;
    return `<div class="${n ? "changed" : ""}"><span>${esc(label(s))}</span><strong>${n ? n + " changed" : "unchanged"}</strong></div>`;
  }).join("")}</div>${table(
    ["System", "Field", "Before", "After"],
    rows.map((x) => [
      esc(label(x.system)),
      `<code>${esc(x.field)}</code>`,
      esc(formatField(x.field, x.before)),
      x.changed ? `<strong class="delta">${esc(formatField(x.field, x.after))}</strong>` : `<span class="muted">${esc(formatField(x.field, x.after))}</span>`,
    ]),
    "diff",
  )}<h3>Action receipt ledger</h3>${
    entries.length
      ? table(["#", "Action", "Effect", "Receipt", "Status"], entries, "ledger")
      : `<p class="muted">${r.plan.actions.length ? "No action has been applied yet. Approve and execute the proposal to create receipts." : "This outcome proposes no actions, so no receipts exist."}</p>`
  }${r.execution?.same_request_retry_no_duplicates ? `<div class="callout">A repeated execute call reused every confirmed receipt. Fixture state and the event log were byte-identical afterwards.</div>` : ""}`;
}
function evidence(r) {
  return `<h2>Executed source evidence</h2><p class="muted">${r.evidence.length} retained system observations, each bound to source version <code>${esc(r.plan.source_version.slice(0, 12))}</code>.</p>${r.evidence.map((v, i) => `<details ${i === 0 ? "open" : ""}><summary>${esc(label(v.system))} · ${esc(v.evidence_id?.slice(0, 12))}</summary>${json(v.data)}</details>`).join("")}`;
}
function checkGroup(value, heading) {
  const entries = Object.entries(value || {}),
    passed = entries.filter(([, ok]) => ok).length;
  return `<div class="check-group"><div class="check-head"><h3>${esc(heading)}</h3><span class="score ${passed === entries.length ? "pass" : "fail"}">${passed}/${entries.length} passed</span></div><div class="check-grid">${entries.map(([name, ok]) => `<div class="check-chip ${ok ? "pass" : "fail"}"><span aria-hidden="true">${ok ? "✓" : "!"}</span>${esc(label(name))}<span class="sr-only">${ok ? "passed" : "needs review"}</span></div>`).join("")}</div></div>`;
}
function verification(r) {
  return `<h2>Independent state checks</h2><p class="muted">The evaluator compares the original and final fixtures directly. It is not imported into the agent's tool definitions.</p>${checkGroup(r.simulation.checks, "Counterfactual fixture simulation")}${r.execution ? checkGroup(r.execution.checks, "Actual sandbox execution") : ""}${r.execution?.reconciled_receipts ? `<div class="callout">${r.execution.reconciled_receipts} uncertain receipt reconciled against observed state before completion.</div>` : ""}`;
}
function activity(r) {
  const steps = {
    "observed-four-systems": ["Observed four systems", "Agent"],
    "proposed-plan": ["Proposed a typed plan", "Agent"],
    "policy-validated": ["Policy validated the plan", "Validator"],
    "simulated-on-private-copy": ["Simulated on a private copy", "Simulator"],
    "awaiting-operator-if-actions": ["Waited for operator review", "Operator"],
  };
  const items = r.activity.map((a) => [...(steps[a] || [label(a), "Workflow"]), ""]);
  for (const e of r.events) {
    if (e.kind === "approved") items.push(["Approved the exact plan", "Operator", e.payload.plan_digest.slice(0, 12)]);
    else if (e.kind === "action_applied")
      items.push([`${ACTIONS[e.payload.kind]} · ${actionValue(e.payload)}`, "Action broker", `receipt ${e.payload.receipt.slice(0, 12)} · ${e.payload.status}`]);
    else if (e.kind === "reconciled") items.push(["Reconciled an uncertain receipt", "Action broker", e.payload.receipt.slice(0, 12)]);
  }
  return `<h2>Executed activity</h2><p class="muted">${items.length} recorded steps from the LangGraph assessment and the sandbox event log.</p><ol class="timeline">${items.map(([text, owner, detail]) => `<li><span class="dot" aria-hidden="true"></span><div><strong>${esc(text)}</strong><small>${esc(owner)}${detail ? " · " + esc(detail) : ""}</small></div></li>`).join("")}</ol><details><summary>Raw event log</summary>${json({ graph: r.activity, events: r.events })}</details>`;
}
function detail(r) {
  if (!r)
    return `<div class="heading"><h1>Report unavailable in this browser.</h1><p class="muted">Public demo history stays in the browser session that ran the investigation.</p><a class="button" href="/demo" data-go="/demo">Start a new investigation</a></div>`;
  const tabs = [
    ["result", "Proposal + action"],
    ["effects", "Effects"],
    ["evidence", "Source evidence"],
    ["checks", "Verification"],
    ["activity", "Activity"],
  ];
  const passed = r.execution?.passed ?? r.simulation.passed;
  const panels = { result, effects, evidence, checks: verification, activity };
  const panel = (panels[activeTab] || result)(r);
  return `<div class="heading"><a class="back" href="/demo#history" data-go="/demo#history">← Investigations</a><div class="eyebrow">INVESTIGATION / ${esc(r.id.slice(0, 8))}</div><div class="section-heading"><h1>${esc(r.title)}</h1><span class="pill">${esc(label(r.stage))}</span></div><p class="muted">${esc(r.mode)} · Four-system fixture</p></div>${stepper(r)}<div class="stats"><div><span>Evidence results</span><strong>${r.evidence.length}</strong></div><div><span>Outcome</span><strong class="word">${esc(label(r.plan.outcome))}</strong></div><div><span>${r.stage === "uncertain" ? "Execution acknowledgment" : "Verification"}</span><strong class="word">${r.stage === "uncertain" ? "Uncertain" : passed ? "Checks passed" : "Review required"}</strong></div></div><div class="grid"><section><div class="tabs" aria-label="Report sections">${tabs.map(([id, name]) => `<button aria-pressed="${activeTab === id}" data-tab="${id}" class="${activeTab === id ? "active" : ""}">${name}</button>`).join("")}</div><div class="card result-card">${panel}${statusUI()}</div></section><aside><div class="card"><div class="eyebrow">TRACEABLE RESULT</div><h3>Retain the evidence.</h3><p class="muted">The report includes the exact proposal, checks, source version and sandbox receipts.</p><button class="secondary" data-action="export">Download report ↓</button><h3>Proposal version</h3><p class="checksum">${esc(r.version)}</p><small>SHA-256 of the case, plan, simulation and source version.</small></div><div class="card"><h3>Scope and persistence</h3><p class="muted">${esc(r.scope)}</p><a href="/demo" data-go="/demo">Start another case →</a></div></aside></div>`;
}
function recordingPage() {
  return `<div class="heading"><a class="back" href="/demo" data-go="/demo">← Workspace</a><div class="eyebrow">ACTUAL BROWSER WALKTHROUGH</div><h1>RelayOps in action.</h1><p class="muted">A continuous recording of the working synthetic application. Browser interactions are automated; no live model call, customer feedback or external business effect.</p></div><section class="card"><video class="walkthrough" controls preload="metadata" poster="/demo-assets/poster.png" src="/demo-assets/walkthrough.webm">Your browser does not support this video. Download the recording below.</video><div class="toolbar"><a class="button secondary" href="/demo-assets/walkthrough.webm" download>Download continuous recording ↓</a><a class="button" href="/demo" data-go="/demo">Run it yourself ↗</a></div></section>`;
}
function render() {
  if (!config) return;
  const path = location.pathname;
  let content, title;
  if (path === "/demo/recording") [content, title] = [recordingPage(), "Recorded demo"];
  else if (path === "/demo/architecture") [content, title] = [architecturePage(), "Architecture"];
  else if (path.startsWith("/demo/runs/")) [content, title] = [detail(current()), "Investigation"];
  else if (location.hash === "#history") [content, title] = [historyPage(), "Investigation history"];
  else [content, title] = [home(), "Interactive workspace"];
  document.title = "RelayOps · " + title;
  app.innerHTML = shell(content);
}
function download(run) {
  const value = { ...run };
  delete value.token;
  delete value.viewed_at;
  const url = URL.createObjectURL(
    new Blob(
      [
        JSON.stringify(
          {
            format: "relayops-sandbox-report-v1",
            exported_at: new Date().toISOString(),
            report: value,
          },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    ),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = "relayops-" + run.id + ".json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
document.addEventListener("change", (event) => {
  if (event.target.id === "case") {
    selectedCase = event.target.value;
    render();
  }
});
document.addEventListener("submit", (event) => {
  if (event.target.id === "start-form") {
    event.preventDefault();
    if (!busy)
      perform("Reading sources and checking the proposal…", "investigate", {
        case_id: document.querySelector("#case").value,
      });
  }
});
document.addEventListener("click", (event) => {
  const target = event.target.closest(
    "[data-go],[data-case],[data-tab],[data-action]",
  );
  if (!target) return;
  if (target.hasAttribute("data-go")) {
    event.preventDefault();
    go(target.dataset.go);
    return;
  }
  if (target.hasAttribute("data-case")) {
    selectedCase = target.dataset.case;
    render();
    document.querySelector("#case")?.focus();
    return;
  }
  if (target.hasAttribute("data-tab")) {
    activeTab = target.dataset.tab;
    render();
    return;
  }
  const action = target.dataset.action,
    r = current();
  if (!r || busy) return;
  if (action === "export") {
    download(r);
    return;
  }
  const token = r.token;
  if (action === "approve" || action === "reject")
    perform(
      "Checking this exact result and recording your decision…",
      "review",
      { token, action },
    );
  else if (action === "execute" || action === "lost-ack")
    perform(
      "Applying approved actions and checking the resulting fixture…",
      "execute",
      {
        token,
        failure_mode: action === "lost-ack" ? "acknowledgment_loss" : "none",
      },
    );
  else if (action === "reconcile")
    perform(
      "Reconciling the uncertain receipt and completing verified actions…",
      "reconcile",
      { token },
    );
});
window.addEventListener("popstate", () => {
  activeTab = "result";
  error = "";
  render();
});
fetch("/api/demo/config", { credentials: "same-origin" })
  .then(async (response) => {
    if (!response.ok)
      throw new Error("The interactive workspace is unavailable.");
    config = await response.json();
    selectedCase = config.cases[0].id;
    const chosen = new URLSearchParams(location.search).get("case");
    if (config.cases.some((c) => c.id === chosen)) selectedCase = chosen;
    render();
  })
  .catch((e) => {
    app.innerHTML = `<div class="loading"><h1>Unable to open the workspace</h1><p>${esc(e.message)}</p><a href="/demo">Reload the demo</a></div>`;
  });
