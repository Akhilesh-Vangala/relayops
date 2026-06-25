"""Independent final-state checks, not imported into model tool definitions."""
def evaluate(original, final, events, outcome):
    shortage = original["procurement"]["ordered_units"] - original["warehouse"]["received_units"]
    uncertain = (not original["warehouse"]["delivery_known"]
                 or original["billing"]["invoiced_units"] != original["procurement"]["ordered_units"]
                 or original["warehouse"]["available_units"] < shortage)
    effects = [event for event in events if event["kind"] == "action_applied"]
    checks = {"scope_preserved": (final["tenant"], final["case_id"]) == (original["tenant"], original["case_id"]),
              "source_order_preserved": final["procurement"] == original["procurement"],
              "source_delivery_preserved": final["warehouse"] == original["warehouse"],
              "invoice_quantity_preserved": final["billing"]["invoiced_units"] == original["billing"]["invoiced_units"],
              "source_documents_preserved": final.get("documents") == original.get("documents")}
    if uncertain or shortage == 0:
        checks.update(correct_outcome=outcome == ("needs_information" if uncertain else "no_change"),
                      no_business_effects=not effects, original_state_preserved=final == original)
    else:
        checks.update(correct_outcome=outcome == "resolve",
                      held_amount=final["billing"]["held_cents"] == shortage * original["procurement"]["unit_cents"],
                      claim_quantity=final["case_management"]["claim_units"] == shortage,
                      reservation_quantity=final["case_management"]["reserved_units"] == shortage,
                      resolved=final["case_management"]["status"] == "resolved",
                      no_duplicate_effects=len(effects) == 4 and len({e["payload"]["kind"] for e in effects}) == 4,
                      explicit_review=any(e["kind"] == "approved" for e in events))
    return {"passed": all(checks.values()), "checks": checks,
            "scope": "Original synthetic short-shipment fixture; not customer or live-model performance"}
