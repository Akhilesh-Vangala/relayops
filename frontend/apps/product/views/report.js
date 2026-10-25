import {
  el,
  title,
  button,
  link,
  icon,
  badge,
  money,
  table,
  download,
  modal,
} from "../lib/dom.js";
import { state } from "../state.js";
import { steps, definition, issueBox } from "./intake.js";
const labels = {
  resolve: "Ready for review",
  needs_information: "Needs information",
  no_change: "No change",
};
function reason(row) {
  const c = row.source_context || {};
  if (row.plan.outcome === "no_change")
    return "No shortage under the supplied snapshot.";
  if (row.plan.outcome === "resolve")
    return "Delivery, invoice and remaining stock support the proposed actions.";
  if (!c.delivery_confirmed)
    return "Delivery is not confirmed; obtain warehouse evidence.";
  if (c.invoiced !== c.ordered)
    return "Invoice quantity differs from the order; reconcile billing evidence.";
  if (c.stock_before_case < row.shortage_units)
    return "Remaining replacement stock cannot cover this case; review allocation.";
  return "Additional evidence is required; no actions are proposed.";
}
function inspect(row) {
  modal(
    "Case " + row.order_id,
    el(
      "div",
      {},
      badge(labels[row.plan.outcome], "outcome-" + row.plan.outcome),
      el("p", { class: "spaced" }, reason(row)),
      el(
        "p",
        { class: "hint spaced" },
        "Source record " + row.source_row + " · Pool " + row.inventory_pool,
      ),
      table(
        ["Proposed action", "Amount / units"],
        row.plan.actions.map((a) => [
          a.kind,
          a.kind === "hold_invoice" ? money(a.amount) : a.amount,
        ]),
        { label: "Exact proposed actions" },
      ),
      el("h3", { class: "spaced" }, "Observed workflow"),
      el("p", { class: "hint spaced" }, row.activity.join(" → ")),
      el(
        "details",
        { class: "spaced" },
        el("summary", {}, "Independent checks and receipts"),
        el(
          "pre",
          {},
          JSON.stringify(
            { checks: row.checks, receipts: row.receipts },
            null,
            2,
          ),
        ),
      ),
    ),
    [
      button(
        "Close",
        () => document.getElementById("dialog").close(),
        "secondary",
      ),
    ],
  );
}
export function reportView(ctx) {
  const draft = state.draft,
    report = draft.report,
    s = report.summary;
  const completed = s.approved_export;
  const [selected, setSelected] = [
    state.reportTab || "overview",
    (v) => {
      state.reportTab = v;
      ctx.render();
      document.getElementById("tab-" + v)?.focus();
    },
  ];
  const tabs = el(
    "div",
    { class: "tabs", role: "tablist", "aria-label": "Assessment sections" },
    ...[
      ["overview", "Case triage"],
      ["stock", "Stock & policy"],
      ["evidence", "Verification"],
    ].map(([id, label]) => {
      const tab = button(label, () => setSelected(id), "", {
        id: "tab-" + id,
        role: "tab",
        "aria-selected": selected === id,
        "aria-controls": "report-panel",
        tabindex: selected === id ? "0" : "-1",
      });
      tab.addEventListener("keydown", (e) => {
        if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) {
          e.preventDefault();
          const ids = ["overview", "stock", "evidence"],
            i = ids.indexOf(id);
          setSelected(
            e.key === "Home"
              ? ids[0]
              : e.key === "End"
                ? ids[2]
                : ids[(i + (e.key === "ArrowRight" ? 1 : 2)) % 3],
          );
        }
      });
      return tab;
    }),
  );
  let panel;
  if (selected === "overview") {
    const search = el("input", {
      type: "search",
      "aria-label": "Search operational cases",
      placeholder: "Search case ID or pool",
      class: "simple-input",
    });
    const filter = el(
      "select",
      { "aria-label": "Filter cases", class: "simple-input" },
      el("option", { value: "" }, "All outcomes"),
      ...Object.entries(labels).map(([id, label]) =>
        el("option", { value: id }, label),
      ),
    );
    const rows = el("div", { class: "spaced" });
    function draw() {
      const visible = report.results.filter(
        (r) =>
          (!filter.value || r.plan.outcome === filter.value) &&
          [r.order_id, r.inventory_pool].some((v) =>
            v.toLowerCase().includes(search.value.toLowerCase()),
          ),
      );
      rows.replaceChildren(
        visible.length
          ? table(
              ["Case", "Outcome", "Shortage", "Pool", "Evidence / review"],
              visible.map((r) => [
                r.order_id,
                badge(labels[r.plan.outcome], "outcome-" + r.plan.outcome),
                r.shortage_units,
                r.inventory_pool,
                button("Inspect case", () => inspect(r), "quiet", {
                  "aria-label": "Inspect " + r.order_id,
                }),
              ]),
              { label: "Source-derived case triage" },
            )
          : el("p", { class: "muted spaced" }, "No matching cases."),
      );
    }
    search.addEventListener("input", draw);
    filter.addEventListener("change", draw);
    draw();
    panel = el(
      "section",
      { class: "panel" },
      el("h2", {}, "Review the cases that need a decision."),
      el(
        "p",
        { class: "hint spaced" },
        "Actions remain proposals until the exact snapshot is approved. Cases needing information never receive a change set.",
      ),
      el("div", { class: "actions spaced" }, search, filter),
      rows,
    );
  } else if (selected === "stock") {
    panel = el(
      "section",
      { class: "panel" },
      el("h2", {}, "Shared stock is allocated once per assessment."),
      el(
        "p",
        { class: "hint spaced" },
        "Cases are processed in sorted order-ID order. These balances are projected against the uploaded snapshot, not live warehouse inventory.",
      ),
      table(
        ["Pool / allocated order", "Projected units remaining"],
        Object.entries(report.inventory_remaining),
        { label: "Projected inventory conservation" },
      ),
      el("div", { class: "spaced" }, definition(draft)),
    );
  } else
    panel = el(
      "section",
      { class: "panel" },
      el("h2", {}, "Evidence before authority."),
      ...Object.entries(report.checks).map(([name, value]) =>
        el(
          "div",
          { class: "check-row spaced" },
          icon("check"),
          el(
            "div",
            {},
            el("strong", {}, name.replaceAll("_", " ")),
            el("p", {}, value ? "Passed" : "Failed"),
          ),
        ),
      ),
      el("p", { class: "muted spaced" }, report.scope),
    );
  const consent = el("input", { type: "checkbox", id: "consent" });
  const approve = button(
    "Approve snapshot & prepare export",
    () => {
      if (consent.checked) ctx.approveExport();
    },
    "primary",
    { id: "approve", disabled: true },
  );
  consent.addEventListener(
    "change",
    () => (approve.disabled = !consent.checked || state.busy),
  );
  const approval = completed
    ? el(
        "div",
        { class: "callout spaced" },
        icon("check"),
        el(
          "p",
          {},
          "Approved snapshot export is ready. Effects were checked in reconstructed temporary worlds. No connected business system was modified.",
        ),
      )
    : draft.restored
      ? el(
          "div",
          { class: "callout spaced" },
          icon("help"),
          el(
            "div",
            {},
            el(
              "p",
              {},
              "This is a saved assessment. Reassess the retained source before approving a fresh browser-bound export.",
            ),
            button(
              "Reassess before approval",
              () => ctx.advance(1),
              "secondary",
              { class: "secondary spaced" },
            ),
          ),
        )
      : el(
          "section",
          { class: "panel spaced" },
          el("h2", {}, "Authorize this snapshot export deliberately."),
          el(
            "p",
            { class: "muted spaced" },
            "Approval recomputes the exact source and plan, executes eligible actions in temporary worlds and verifies receipts. It does not contact an ERP, supplier, payment or inventory service.",
          ),
          el(
            "label",
            { class: "checkbox spaced" },
            consent,
            "I reviewed the cases, proposed actions and stock allocation. Prepare the checked downloadable change set.",
          ),
          el("div", { class: "actions spaced" }, approve),
        );
  return el(
    "div",
    { id: "output" },
    title(
      "OPERATIONAL ASSESSMENT",
      draft.title,
      draft.filename + " · " + s.cases + " cases",
      [
        button("Edit rules & reassess", () => ctx.advance(1), "secondary"),
        button("Save investigation", ctx.save),
        button("Clear workspace", ctx.clear, "quiet", { id: "clear" }),
      ],
    ),
    steps(3),
    issueBox(ctx),
    el(
      "section",
      { class: "finding-hero" },
      el(
        "p",
        { class: "eyebrow" },
        completed ? "CHECKED SNAPSHOT EXPORT" : "REVIEW BEFORE ACTION",
      ),
      el(
        "h2",
        {},
        completed
          ? "A checked change set, with receipts."
          : s.needs_information
            ? "Resolve the supported cases. Clarify the rest."
            : "Your proposed actions are ready for review.",
      ),
      el(
        "p",
        {},
        `Ready for review: ${s.resolvable}. More evidence needed: ${s.needs_information}. No change needed: ${s.no_change}.`,
      ),
      el(
        "div",
        { id: "verification", class: "spaced" },
        badge("Independent checks passed"),
      ),
    ),
    el(
      "div",
      { class: "stats spaced" },
      ...[
        ["Cases assessed", s.cases, "Actual source records"],
        ["Need information", s.needs_information, "No actions proposed"],
        [
          "Proposed invoice hold",
          money(s.proposed_hold_cents),
          "Snapshot proposal, not a payment",
        ],
      ].map(([label, value, hint]) =>
        el(
          "div",
          { class: "stat" },
          el("span", { class: "stat-label" }, label),
          el("strong", {}, value),
          el("small", {}, hint),
        ),
      ),
    ),
    tabs,
    el(
      "div",
      {
        id: "report-panel",
        role: "tabpanel",
        "aria-labelledby": "tab-" + selected,
      },
      panel,
    ),
    approval,
    el(
      "section",
      { class: "panel spaced" },
      el(
        "div",
        { class: "panel-heading" },
        el("h2", {}, "Keep the evidence with the decision."),
        badge(draft.storage === "memory" ? "Not saved" : "Saved snapshot"),
      ),
      el(
        "div",
        { class: "actions spaced" },
        button("Download evidence JSON", ctx.exportReport, "secondary", {
          id: "download-json",
        }),
        button(
          "Download checked changes CSV",
          () => {
            if (report.csv)
              download(report.csv, "relayops-checked-changes.csv", "text/csv");
          },
          "primary",
          { id: "download-csv", disabled: !report.csv },
        ),
      ),
      el(
        "p",
        { class: "hint mono spaced" },
        "Source SHA-256 · " + report.source_sha256,
      ),
      el(
        "details",
        { id: "evidence", class: "spaced" },
        el("summary", {}, "Complete assessment evidence"),
        el(
          "pre",
          {},
          JSON.stringify(
            Object.fromEntries(
              Object.entries(report).filter(([key]) => key !== "review"),
            ),
            null,
            2,
          ),
        ),
      ),
    ),
    el(
      "div",
      { class: "trust-strip" },
      el("span", {}, "LangGraph · known diagnostic"),
      el("span", {}, "Exact-source approval"),
      el("span", {}, "No external system writes"),
    ),
  );
}
