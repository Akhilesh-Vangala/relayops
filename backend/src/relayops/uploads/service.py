"""Upload-derived worlds: real LangGraph assessment, reviewed local exports only."""
import hashlib
import asyncio
import tempfile
from pathlib import Path

from relayops.agents.planner import DiagnosticPlanner
from relayops.agents.workflow import build_workflow
from relayops.domain.environment import World
from relayops.domain.models import digest
from relayops.execution.executor import approve, execute
from relayops.verification.evaluator import evaluate

from .ingestion import UploadProblem, column, decimal_value, fingerprint, integer, parse, safe_csv


def run(upload, *, approved=False, progress=None):
    progress = progress or (lambda stage, state: None)
    progress("source", "running")
    headers, rows = parse(upload.csv)
    progress("source", "complete")
    progress("contract", "running")
    required = ("order_id", "ordered", "received", "invoiced", "available", "unit_price", "confirmed")
    if set(upload.mapping) - set(required) - {"pool"} or set(upload.options) - {"unit"}:
        raise ValueError("Unsupported case contract fields")
    if len(rows) > 30:
        raise ValueError("Operational assessment supports at most 30 open cases per export")
    columns = {name: column(upload.mapping, name, headers) for name in required}
    pool_col = column(upload.mapping, "pool", headers, True)
    unit = upload.options.get("unit", "dollars")
    if unit not in ("dollars", "cents"):
        raise ValueError("Choose dollars or cents")
    cases, seen, balances = [], set(), {}
    def issue(number, field, message):
        raise UploadProblem(message, code="case_contract", issues=[{"row": number, "column": headers[columns[field]], "message": message}],
                            hint="Inspect the affected record and correct the source or mapping. No actions or export were created.")
    for number, row in enumerate(rows, 2):
        order_id = row[columns["order_id"]].strip()
        if not 1 <= len(order_id) <= 80 or order_id in seen:
            issue(number, "order_id", "Order IDs must be nonempty, unique and at most 80 characters")
        seen.add(order_id)
        pool = row[pool_col].strip() if pool_col is not None else order_id
        if not pool:
            raise ValueError("Inventory pool cannot be blank")
        values = {}
        for name in ("ordered", "received", "invoiced", "available"):
            try:
                values[name] = integer(row[columns[name]])
            except ValueError as error:
                issue(number, name, str(error))
        try:
            cents = int(decimal_value(row[columns["unit_price"]], places=2 if unit == "dollars" else 0, nonnegative=True)*(100 if unit == "dollars" else 1))
        except ValueError as error:
            issue(number, "unit_price", str(error))
        confirmation = row[columns["confirmed"]].strip().lower()
        if confirmation not in ("true", "false"):
            issue(number, "confirmed", "Delivery confirmation must explicitly be true or false")
        if values["received"] > values["ordered"]:
            issue(number, "received", "Overdelivery requires a different contract; no automatic resolution")
        if (values["ordered"]-values["received"])*cents > 10_000_000 or max(values.values()) > 10_000_000:
            raise ValueError("Case exceeds the existing action policy bounds")
        if pool in balances and balances[pool] != values["available"]:
            raise ValueError("Rows sharing an inventory pool must declare the same initial stock")
        balances[pool] = values["available"]
        cases.append((order_id, pool, values, cents, confirmation == "true"))
    reports, updates = [], []
    progress("contract", "complete")
    progress("workflow", "running")
    # Stable order and pool accounting prevent oversubscription across case rows.
    for order_id, pool, values, cents, known in sorted(cases):
        source = {"tenant": "upload", "case_id": order_id,
                  "procurement": {"order_id": order_id, "ordered_units": values["ordered"], "unit_cents": cents},
                  "warehouse": {"received_units": values["received"], "delivery_known": known, "available_units": balances[pool]},
                  "billing": {"invoiced_units": values["invoiced"], "held_cents": 0},
                  "case_management": {"status": "open", "claim_units": 0, "reserved_units": 0},
                  "documents": {}}
        with tempfile.TemporaryDirectory(prefix="relayops-upload-") as directory:
            world = World(Path(directory)/"case.sqlite")
            world.initialize(source)
            assessment = asyncio.run(build_workflow(world, DiagnosticPlanner()).ainvoke({}))
            plan = assessment["plan"]
            final = source
            if approved and plan.actions:
                approval = approve(world, plan, operator="browser-review-export")
                final = execute(world, plan, approval)
                verification = evaluate(source, final, world.events(), plan.outcome)
                if not verification["passed"]:
                    raise ValueError("Final-state verification failed; export withheld")
            else:
                verification = assessment["simulation"]
            shortage = values["ordered"]-values["received"]
            if plan.outcome == "resolve":
                balances[pool] -= shortage
            reports.append({"order_id": order_id, "inventory_pool": pool, "source_row": next(i+2 for i, r in enumerate(rows) if r[columns["order_id"]].strip() == order_id),
                            "source_context": {**values, "delivery_confirmed": known, "stock_before_case": source["warehouse"]["available_units"]},
                            "shortage_units": shortage, "unit_cents": cents,
                            "plan": plan.model_dump(mode="json"),
                            "plan_sha256": digest(plan.model_dump(mode="json")),
                            "checks": verification["checks"], "passed": verification["passed"],
                            "activity": assessment["activity"],
                            "receipts": [e["payload"] for e in world.events() if e["kind"] == "action_applied"] if approved else []})
            updates.append([order_id, plan.outcome, final["billing"]["held_cents"],
                            final["case_management"]["claim_units"], final["case_management"]["reserved_units"],
                            final["case_management"]["status"]])
    progress("workflow", "complete")
    progress("reconcile", "running")
    if not all(r["passed"] for r in reports) or any(n < 0 for n in balances.values()):
        raise ValueError("Independent case or stock checks failed; report withheld")
    progress("reconcile", "complete")
    progress("report", "running")
    result = {"project": "RelayOps", "mode": "known-contract-langgraph", "live_ai": False,
            "source_sha256": hashlib.sha256(upload.csv.encode()).hexdigest(), "contract": {"mapping": upload.mapping, "options": upload.options},
            "summary": {"cases": len(reports), "resolvable": sum(r["plan"]["outcome"] == "resolve" for r in reports),
                        "needs_information": sum(r["plan"]["outcome"] == "needs_information" for r in reports), "approved_export": approved,
                        "no_change": sum(r["plan"]["outcome"] == "no_change" for r in reports),
                        "proposed_hold_cents": sum(r["shortage_units"]*r["unit_cents"] for r in reports if r["plan"]["outcome"] == "resolve")},
            "column_bindings": {f"c{i}": h for i, h in enumerate(headers)},
            "checks": {"all_cases_independently_verified": all(r["passed"] for r in reports), "inventory_pools_not_oversubscribed": all(n >= 0 for n in balances.values())},
            "results": reports, "inventory_remaining": balances,
            "plan_sha256": fingerprint([r["plan_sha256"] for r in reports]),
            "csv": safe_csv(["order_id", "outcome", "held_cents", "claim_units", "reserved_units", "status"], updates) if approved else None,
            "scope": "Open, previously unprocessed cases only. Stock is shared only when an inventory-pool column is mapped; otherwise each order has separately allocated stock. Approval creates a checked downloadable change set against a temporary snapshot. No ERP, supplier, payment or inventory system is modified.",
            "activity": ["validate-open-case-export", "observe-upload-worlds", "langgraph-propose-policy-simulate", "review-exact-source-and-plan", "verify-exported-effects" if approved else "await-review"]}
    progress("report", "complete")
    return result
