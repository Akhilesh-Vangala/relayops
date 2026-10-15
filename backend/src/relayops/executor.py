"""Explicit approvals and idempotent sandbox action receipts."""
import json
import secrets

from .domain import Plan, Refused, digest
from .policy import validate


def approve(world, plan: Plan, *, operator):
    if not operator.strip() or len(operator) > 80:
        raise Refused("An explicit operator identity label is required")
    with world.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        validate(world, plan, db)
        if not plan.actions:
            raise Refused("There are no actions to approve")
        identity = secrets.token_hex(24)
        db.execute("INSERT INTO approvals VALUES (?,?,?,?,?)",
                   (identity, digest(plan.model_dump(mode="json")), plan.tenant, "approved", operator))
        db.execute("INSERT INTO events(kind,payload) VALUES ('approved',?)",
                   (json.dumps({"plan_digest": digest(plan.model_dump(mode="json")), "operator": operator}),))
        return identity


def execute(world, plan: Plan, approval, *, timeout_after=None, crash_before=None):
    """One action per transaction; atomicity is only inside the fixture backend."""
    plan_hash = digest(plan.model_dump(mode="json"))
    for index, action in enumerate(plan.actions):
        receipt_id = digest({"plan": plan_hash, "action": index})
        if crash_before == index:
            raise InterruptedError("Injected worker crash before next action")
        with world.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            validate(world, plan, db)
            approval_row = db.execute("SELECT * FROM approvals WHERE id=?", (approval,)).fetchone()
            if approval_row is None or approval_row["digest"] != plan_hash or approval_row["tenant"] != plan.tenant:
                raise Refused("Missing approval or approved plan differs from this proposal")
            if approval_row["status"] != "approved":
                raise Refused("Approval is not active")
            previous = db.execute("SELECT * FROM receipts WHERE id=?", (receipt_id,)).fetchone()
            if previous:
                if previous["status"] != "confirmed":
                    raise Refused("Uncertain action outcome; reconcile before continuing")
                continue
            state = world.state(db)
            if action.kind == "hold_invoice":
                if state["billing"]["held_cents"]:
                    raise Refused("Existing billing hold requires reconciliation")
                state["billing"]["held_cents"] = action.amount
            elif action.kind == "open_supplier_claim":
                if state["case_management"]["claim_units"]:
                    raise Refused("Existing supplier claim requires reconciliation")
                state["case_management"]["claim_units"] = action.amount
            elif action.kind == "reserve_replacement":
                if state["case_management"]["reserved_units"]:
                    raise Refused("Existing reservation requires reconciliation")
                state["case_management"]["reserved_units"] = action.amount
            elif action.kind == "resolve_case":
                shortage = state["procurement"]["ordered_units"] - state["warehouse"]["received_units"]
                if (state["billing"]["held_cents"] != shortage * state["procurement"]["unit_cents"]
                        or state["case_management"]["claim_units"] != shortage
                        or state["case_management"]["reserved_units"] != shortage):
                    raise Refused("Required business effects are not confirmed")
                state["case_management"]["status"] = "resolved"
            status = "unknown" if timeout_after == index else "confirmed"
            payload = {"kind": action.kind, "amount": action.amount, "tenant": plan.tenant, "case_id": plan.case_id}
            db.execute("UPDATE state SET payload=? WHERE id=1", (json.dumps(state),))
            db.execute("INSERT INTO receipts VALUES (?,?,?,?,?)", (receipt_id, plan_hash, index, status, json.dumps(payload)))
            db.execute("INSERT INTO events(kind,payload) VALUES ('action_applied',?)", (json.dumps({**payload, "receipt": receipt_id, "status": status}),))
        if status == "unknown":
            raise TimeoutError("Injected acknowledgement loss; action may already have applied")
    return world.state()


def reconcile(world, plan: Plan, approval):
    """Inspect fixture business state; never resend an uncertain action."""
    plan_hash = digest(plan.model_dump(mode="json"))
    with world.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        validate(world, plan, db)
        approved = db.execute("SELECT * FROM approvals WHERE id=?", (approval,)).fetchone()
        if approved is None or approved["digest"] != plan_hash or approved["status"] != "approved":
            raise Refused("Exact active approval required for reconciliation")
        state = world.state(db)
        effects = {"hold_invoice": state["billing"]["held_cents"],
                   "open_supplier_claim": state["case_management"]["claim_units"],
                   "reserve_replacement": state["case_management"]["reserved_units"],
                   "resolve_case": 0 if state["case_management"]["status"] == "resolved" else None}
        rows = list(db.execute("SELECT * FROM receipts WHERE plan_digest=? AND status='unknown'", (plan_hash,)))
        for row in rows:
            payload = json.loads(row["payload"])
            if effects[payload["kind"]] != payload["amount"]:
                raise Refused("Business state cannot establish the uncertain action outcome")
            db.execute("UPDATE receipts SET status='confirmed' WHERE id=?", (row["id"],))
            db.execute("INSERT INTO events(kind,payload) VALUES ('reconciled',?)", (json.dumps({"receipt": row["id"]}),))
        return len(rows)
