import { el, link, button, icon, badge } from "../lib/dom.js";
export function brand(href = "/") {
  return link(
    [
      el("span", { class: "brand-symbol", "aria-hidden": "true" }, "r/"),
      "RelayOps",
    ],
    href,
    "brand",
    { id: "brand" },
  );
}
export function landing(ctx) {
  const proof = el(
    "div",
    {
      class: "hero-proof",
      "aria-label": "Illustrative sample assessment, not your data",
    },
    el(
      "div",
      { class: "proof-top" },
      el("span", {}, "SHORT-SHIPMENT REVIEW"),
      badge("Sample assessment"),
    ),
    el(
      "div",
      { class: "proof-body" },
      el("p", { class: "eyebrow" }, "BEFORE ANY CHANGE"),
      el("strong", { class: "proof-amount" }, "Evidence. Then action."),
      el(
        "p",
        { class: "hint spaced" },
        "Observe the snapshot. Challenge the plan. Keep a human decision in the loop.",
      ),
      ...[
        "Policy and simulation before review",
        "Shared stock conserved across cases",
        "Receipts only after explicit approval",
      ].map((t) => el("div", { class: "proof-line" }, icon("check"), t)),
    ),
    el(
      "div",
      { class: "proof-footer" },
      "No connected ERP, supplier or payment system is modified.",
    ),
  );
  return el(
    "div",
    { class: "marketing" },
    el(
      "header",
      { class: "marketing-header" },
      brand(),
      el(
        "nav",
        { "aria-label": "Main navigation" },
        link("How it works", "#how-it-works"),
        link("Documentation", "/workspace/guide"),
        link("Open workspace", "/workspace", "primary"),
      ),
    ),
    el(
      "main",
      { id: "main", class: "marketing-main" },
      el(
        "section",
        { class: "marketing-hero" },
        el(
          "div",
          {},
          badge("OPERATIONS, WITH VERIFIED OUTCOMES"),
          el("h1", {}, "Resolve exceptions.\nVerify every change."),
          el(
            "p",
            { class: "lead" },
            "Bring your open cases. Review source-grounded plans, keep shared stock consistent and prepare a checked change set with evidence for every decision.",
          ),
          el(
            "div",
            { class: "actions" },
            link(
              ["Assess your cases", icon("arrow")],
              "/uploads?new=1",
              "primary",
            ),
            button("Try a sample file", ctx.sample, "secondary"),
          ),
          el(
            "p",
            { class: "hint spaced" },
            "Start without an account. Saving is an explicit choice.",
          ),
        ),
        proof,
      ),
      el(
        "div",
        { class: "marketing-divider" },
        ...[
          "LangGraph assessment",
          "Human approval",
          "Independent state checks",
        ].map((t) => el("span", {}, icon("shield"), t)),
      ),
      el(
        "section",
        { id: "how-it-works", class: "marketing-section" },
        el("p", { class: "eyebrow" }, "A CAREFUL PATH TO A REVIEWED OUTCOME"),
        el("h2", {}, "Know what changes. Know why."),
        el(
          "div",
          { class: "marketing-steps" },
          ...[
            [
              "01 / BRING THE EVIDENCE",
              "Inspect the source.",
              "Upload open order, warehouse and invoice fields. Review delivery confirmation and how stock is allocated.",
            ],
            [
              "02 / CHALLENGE THE PLAN",
              "Assess each case.",
              "The known-rule LangGraph workflow observes, proposes, checks policy and simulates in an isolated temporary world.",
            ],
            [
              "03 / AUTHORIZE THE SNAPSHOT",
              "Keep the receipts.",
              "Inspect cases needing information, approve supported actions and export independently checked changes. No live business writes.",
            ],
          ].map(([n, h, p]) =>
            el(
              "article",
              {},
              el("span", { class: "step-label" }, n),
              el("h3", {}, h),
              el("p", {}, p),
            ),
          ),
        ),
      ),
      el(
        "section",
        { class: "marketing-section" },
        el("p", { class: "eyebrow" }, "WORK THAT CAN BE REVIEWED"),
        el("h2", {}, "Evidence stays with the decision."),
        el(
          "p",
          {},
          "Save a deliberate device snapshot, organize projects, resume after reload or transfer a validated backup to another browser. Public assessment uses a known diagnostic, not live model inference.",
        ),
      ),
      el(
        "section",
        { class: "marketing-cta" },
        el(
          "div",
          {},
          el("h2", {}, "Bring the cases that need a decision."),
          el("p", {}, "Use a snapshot you are authorized to share."),
        ),
        link(
          ["Start an assessment", icon("arrow")],
          "/uploads?new=1",
          "primary",
        ),
      ),
      el(
        "footer",
        { class: "marketing-footer" },
        el("span", {}, "RelayOps · Evidence to verified action"),
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
