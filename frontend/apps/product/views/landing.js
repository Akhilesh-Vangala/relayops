import { el, link, button, icon } from "../lib/dom.js";
export function brand(href = "/") {
  return link(
    [
      el(
        "span",
        { class: "brand-symbol", "aria-hidden": "true" },
        icon("relay"),
      ),
      "RelayOps",
    ],
    href,
    "brand",
    { id: "brand" },
  );
}
const SOURCES = [
  ["Procurement", "PO-2041 · 100 units at $25.00"],
  ["Warehouse", "80 received · delivery confirmed"],
  ["Billing", "100 units invoiced"],
  ["Case management", "open short-shipment case"],
];
const GATES = [
  ["Policy", "recomputes the exact actions"],
  ["Simulation", "private copy of the world"],
  ["Evaluator", "12 / 12 final-state checks"],
  ["Approval", "binds the plan digest"],
  ["Receipts", "4 confirmed · reconciled"],
];
const STEPS = [
  [
    "Observe",
    "The investigator reads procurement, warehouse, billing and case systems, and captures source pages as evidence.",
  ],
  [
    "Propose",
    "A typed, cited plan names an outcome and up to four actions. Policy recomputes what the actions must be.",
  ],
  [
    "Simulate",
    "The plan runs against a private copy. An evaluator outside the model's tools checks the final state.",
  ],
  [
    "Approve",
    "A person reviews the exact plan. Approval is bound to its digest, so any change invalidates it.",
  ],
  [
    "Execute",
    "Each action writes a receipt. Unknown receipts halt the run until reconciliation confirms business state.",
  ],
];
const CHECKS = [
  "scope_preserved",
  "source_order_preserved",
  "source_delivery_preserved",
  "invoice_quantity_preserved",
  "source_documents_preserved",
  "correct_outcome",
  "held_amount",
  "claim_quantity",
  "reservation_quantity",
  "resolved",
  "no_duplicate_effects",
  "explicit_review",
];
const ACTIONS = [
  "hold_invoice",
  "open_supplier_claim",
  "reserve_replacement",
  "resolve_case",
];
function relayStage() {
  return el(
    "section",
    {
      class: "relay-stage",
      "aria-label": "Example resolution of a short shipment",
    },
    el(
      "div",
      { class: "relay-head" },
      el("span", { class: "relay-dot", "aria-hidden": "true" }),
      el("span", {}, "Sandbox case · short shipment of 20 units"),
    ),
    el(
      "div",
      { class: "relay-grid" },
      el(
        "ol",
        { class: "relay-column sources" },
        ...SOURCES.map(([name, detail]) =>
          el(
            "li",
            { class: "relay-node" },
            el("strong", {}, name),
            el("span", {}, detail),
          ),
        ),
      ),
      el(
        "div",
        { class: "relay-core", "aria-hidden": "true" },
        el("span", { class: "core-ring" }),
        el("span", { class: "core-ring delayed" }),
        el(
          "div",
          { class: "core-body" },
          icon("relay"),
          el("strong", {}, "LangGraph"),
          el("span", {}, "investigator"),
        ),
      ),
      el(
        "ol",
        { class: "relay-column gates" },
        ...GATES.map(([name, detail]) =>
          el(
            "li",
            { class: "relay-node gate" },
            icon("check", "icon gate-check"),
            el("div", {}, el("strong", {}, name), el("span", {}, detail)),
          ),
        ),
      ),
    ),
  );
}
function bento() {
  return el(
    "div",
    { class: "bento" },
    el(
      "article",
      { class: "bento-card wide" },
      el("span", { class: "bento-icon" }, icon("layers")),
      el("h3", {}, "Counterfactual simulation"),
      el(
        "p",
        {},
        "Every plan executes first against a private copy. You see the business-state diff before anything is approved.",
      ),
      el(
        "div",
        { class: "mini-diff", "aria-label": "Illustrative state diff" },
        ...[
          ["billing.held_cents", "0", "50000"],
          ["case_management.claim_units", "0", "20"],
          ["case_management.reserved_units", "0", "20"],
          ["case_management.status", "open", "resolved"],
        ].map(([field, before, after]) =>
          el(
            "div",
            { class: "diff-line" },
            el("code", {}, field),
            el("span", { class: "before" }, before),
            el("span", { class: "arrow", "aria-hidden": "true" }, "→"),
            el("span", { class: "after" }, after),
          ),
        ),
      ),
    ),
    el(
      "article",
      { class: "bento-card" },
      el("span", { class: "bento-icon" }, icon("lock")),
      el("h3", {}, "Exact-digest approval"),
      el(
        "p",
        {},
        "Approval signs the digest of one specific plan. Edit a single field and the approval no longer applies.",
      ),
      el("code", { class: "digest" }, "sha256 · 9f3a 07c2 … 5be1 c41e"),
    ),
    el(
      "article",
      { class: "bento-card" },
      el("span", { class: "bento-icon" }, icon("shield")),
      el("h3", {}, "Independent evaluator"),
      el(
        "p",
        {},
        "Final-state checks live outside the model's tool set. A resolution must pass all twelve.",
      ),
      el(
        "div",
        {
          class: "chip-grid",
          "aria-label": "Evaluator checks for a resolution",
        },
        ...CHECKS.map((name) =>
          el("span", { class: "chip", title: name }, name.replaceAll("_", " ")),
        ),
      ),
    ),
    el(
      "article",
      { class: "bento-card" },
      el("span", { class: "bento-icon" }, icon("receipt")),
      el("h3", {}, "Receipted execution"),
      el(
        "p",
        {},
        "Each action is keyed by the plan and its position, so retries never apply an effect twice.",
      ),
      el(
        "ul",
        { class: "mini-ledger" },
        ...ACTIONS.map((kind, index) =>
          el(
            "li",
            {},
            el(
              "span",
              { class: "ledger-index" },
              String(index + 1).padStart(2, "0"),
            ),
            el("code", {}, kind),
            el("span", { class: "ledger-state" }, "confirmed"),
          ),
        ),
      ),
    ),
    el(
      "article",
      { class: "bento-card" },
      el("span", { class: "bento-icon" }, icon("clock")),
      el("h3", {}, "Durable runs"),
      el(
        "p",
        {},
        "Runs are leased from PostgreSQL with SKIP LOCKED and resume from LangGraph checkpoints after a worker dies.",
      ),
      el(
        "div",
        { class: "lease-track", "aria-hidden": "true" },
        el("span", { class: "lease a" }),
        el("span", { class: "lease b" }),
        el("span", { class: "lease c" }),
      ),
      el("p", { class: "fine" }, "60 s leases · renewed every 10 s"),
    ),
    el(
      "article",
      { class: "bento-card full" },
      el("span", { class: "bento-icon" }, icon("eye")),
      el("h3", {}, "Evidence you can open"),
      el(
        "p",
        {},
        "Plans must cite between four and twelve evidence records. Source pages are captured with Playwright and attached to the run, so a reviewer checks the same pages the agent read.",
      ),
      el(
        "div",
        { class: "evidence-strip", "aria-hidden": "true" },
        ...["purchase order", "goods receipt", "invoice", "support case"].map(
          (name) => el("span", { class: "evidence-tile" }, el("i", {}), name),
        ),
      ),
    ),
  );
}
function receiptLog() {
  const lines = [
    ["plan", "4f1c 92ae … d07b", "proposed"],
    ["policy", "4 actions recomputed", "match"],
    ["simulation", "12 / 12 checks", "pass"],
    ["approval", "digest 9f3a … c41e", "bound"],
    ["hold_invoice", "receipt r·01", "confirmed"],
    ["open_supplier_claim", "receipt r·02", "confirmed"],
    ["reserve_replacement", "receipt r·03", "confirmed"],
    ["resolve_case", "receipt r·04", "confirmed"],
    ["reconcile", "business state", "matches plan"],
  ];
  return el(
    "div",
    { class: "terminal", "aria-label": "Illustrative execution log" },
    el(
      "div",
      { class: "terminal-bar", "aria-hidden": "true" },
      el("i", {}),
      el("i", {}),
      el("i", {}),
      el("span", {}, "run · PO-2041"),
    ),
    el(
      "ol",
      { class: "terminal-body" },
      ...lines.map(([step, detail, state]) =>
        el(
          "li",
          {},
          el("span", { class: "t-step" }, step),
          el("span", { class: "t-detail" }, detail),
          el("span", { class: "t-state" }, state),
        ),
      ),
    ),
  );
}
export function landing(ctx) {
  return el(
    "div",
    { class: "signal" },
    el("div", { class: "signal-aurora", "aria-hidden": "true" }),
    el(
      "header",
      { class: "signal-nav" },
      brand(),
      el(
        "nav",
        { "aria-label": "Main navigation" },
        link("How it works", "#how-it-works"),
        link("Architecture", "/demo/architecture"),
        link("Sandbox", "/demo"),
        link("Documentation", "/workspace/guide"),
        link("Open workspace", "/workspace", "primary"),
      ),
    ),
    el(
      "main",
      { id: "main", class: "signal-main" },
      el(
        "section",
        { class: "signal-hero" },
        link(
          [
            el("span", { class: "pulse", "aria-hidden": "true" }),
            "Interactive sandbox, no sign-up",
            icon("arrow"),
          ],
          "/demo",
          "signal-pill",
        ),
        el(
          "h1",
          {},
          "Resolve exceptions.",
          el("br"),
          el("span", { class: "gradient-text" }, "Verify every change."),
        ),
        el(
          "p",
          { class: "lead" },
          "An evidence-grounded LangGraph agent for short-shipment exceptions across purchasing, warehouse, billing and support. The model proposes. Policy, simulation and an independent evaluator decide what is allowed. You approve the exact plan.",
        ),
        el(
          "div",
          { class: "actions hero-actions" },
          link(
            ["Assess your cases", icon("arrow")],
            "/uploads?new=1",
            "primary glow",
          ),
          button("Try a sample file", ctx.sample, "secondary"),
        ),
        el(
          "ul",
          { class: "hero-meta" },
          ...[
            "No account required",
            "Synthetic sandbox",
            "No external business writes",
          ].map((t) => el("li", {}, icon("check"), t)),
        ),
      ),
      relayStage(),
      el(
        "section",
        { class: "signal-metrics", "aria-label": "System facts" },
        ...[
          ["12", "final-state checks on every resolution"],
          ["4", "receipted actions, each applied once"],
          ["5", "import formats: CSV, TSV, XLSX, JSON, JSONL"],
          ["0", "writes to external business systems"],
        ].map(([value, label]) =>
          el(
            "div",
            { class: "metric" },
            el("strong", {}, value),
            el("span", {}, label),
          ),
        ),
      ),
      el(
        "section",
        { id: "how-it-works", class: "signal-section" },
        el("p", { class: "signal-eyebrow" }, "Pipeline"),
        el("h2", {}, "Five gates between a model and your ledger."),
        el(
          "ol",
          { class: "pipeline" },
          ...STEPS.map(([name, text], index) =>
            el(
              "li",
              {},
              el(
                "span",
                { class: "pipeline-index" },
                String(index + 1).padStart(2, "0"),
              ),
              el("h3", {}, name),
              el("p", {}, text),
            ),
          ),
        ),
      ),
      el(
        "section",
        { class: "signal-section" },
        el("p", { class: "signal-eyebrow" }, "Capabilities"),
        el("h2", {}, "Built like infrastructure, not a chat window."),
        bento(),
      ),
      el(
        "section",
        { class: "signal-section receipt-section" },
        el(
          "div",
          { class: "receipt-copy" },
          el("p", { class: "signal-eyebrow" }, "Execution"),
          el("h2", {}, "Every action leaves a receipt."),
          el(
            "p",
            {},
            "A receipt identifier is the digest of the approved plan and the action's position. If an outcome is unknown, the run stops; reconciliation reads business state and only then continues.",
          ),
          el(
            "ul",
            { class: "receipt-points" },
            ...[
              "Retries are idempotent by construction",
              "Unknown outcomes block progress",
              "Reconciliation compares state, not logs",
            ].map((t) => el("li", {}, icon("check"), t)),
          ),
        ),
        receiptLog(),
      ),
      el(
        "section",
        { class: "signal-cta" },
        el(
          "div",
          {},
          el("h2", {}, "Bring the cases that need a decision."),
          el(
            "p",
            {},
            "Upload an export you are authorized to share, or walk the guided sandbox first.",
          ),
        ),
        el(
          "div",
          { class: "actions" },
          link(
            ["Start an assessment", icon("arrow")],
            "/uploads?new=1",
            "primary glow",
          ),
          link(
            [icon("play"), "Watch the sandbox"],
            "/demo/recording",
            "secondary",
          ),
        ),
      ),
      el(
        "footer",
        { class: "signal-footer" },
        el(
          "span",
          { class: "brand" },
          el(
            "span",
            { class: "brand-symbol", "aria-hidden": "true" },
            icon("relay"),
          ),
          "RelayOps",
        ),
        el("span", {}, "Evidence to verified action"),
        el(
          "div",
          { class: "actions" },
          link("Data handling", "/workspace/settings"),
          link("Guided demo", "/demo"),
          link("GitHub ↗", "https://github.com/Akhilesh-Vangala/relayops", "", {
            target: "_blank",
            rel: "noreferrer",
          }),
        ),
      ),
    ),
  );
}
