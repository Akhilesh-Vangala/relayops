"""Deterministic action admission; public rules are not evaluation answers."""
from .domain import Plan, Refused
from .environment import SYSTEMS


def validate(world, plan: Plan, db=None):
    state = world.state(db)
    if (plan.tenant, plan.case_id) != (state["tenant"], state["case_id"]):
        raise Refused("Plan scope mismatch")
    if plan.source_version != world.version(db):
        raise Refused("Source changed; refresh evidence and obtain new approval")
    if db is None:
        with world.connect() as connection:
            return validate(world, plan, connection)
    if len(set(plan.evidence_ids)) != len(plan.evidence_ids):
        raise Refused("Duplicate citations")
    rows = [db.execute("SELECT * FROM evidence WHERE id=?", (identity,)).fetchone() for identity in plan.evidence_ids]
    if any(row is None or row["tenant"] != plan.tenant or row["version"] != plan.source_version for row in rows):
        raise Refused("Forged, cross-tenant or stale evidence")
    if {row["system"] for row in rows} != set(SYSTEMS):
        raise Refused("Evidence from every relevant system is required")
    order, delivery, billing = state["procurement"], state["warehouse"], state["billing"]
    shortage = order["ordered_units"] - delivery["received_units"]
    if shortage < 0:
        raise Refused("Over-delivery is outside this workflow contract")
    if not delivery["delivery_known"] or billing["invoiced_units"] != order["ordered_units"]:
        expected = "needs_information"
    elif shortage == 0:
        expected = "no_change"
    elif delivery["available_units"] < shortage:
        expected = "needs_information"
    else:
        expected = "resolve"
    if plan.outcome != expected:
        raise Refused("Plan outcome does not meet the declared workflow contract")
    if expected != "resolve":
        if plan.actions:
            raise Refused("Unresolved or healthy case cannot mutate business systems")
        return
    expected_actions = [("hold_invoice", shortage * order["unit_cents"]),
                        ("open_supplier_claim", shortage), ("reserve_replacement", shortage), ("resolve_case", 0)]
    if [(action.kind, action.amount) for action in plan.actions] != expected_actions:
        raise Refused("Action amounts/order violate the short-shipment contract")
