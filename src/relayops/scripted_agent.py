"""Adaptive scripted client for integration checks; no AI-quality claim."""
import json

from .planner import DiagnosticPlanner


class ScriptedAgent:
    mode = "scripted-agent-integration"

    def __init__(self, *, incorrect_first=False, interrupt_round=None):
        self.incorrect_first, self.interrupt_round = incorrect_first, interrupt_round

    async def complete(self, system, messages, tools, round_number, max_tokens):
        if round_number == self.interrupt_round:
            raise InterruptedError("Injected process interruption before model response")
        records = []
        for message in messages:
            if message["role"] != "user" or not isinstance(message["content"], list):
                continue
            for reply in message["content"]:
                content = reply.get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if block.get("type") == "text":
                        try:
                            value = json.loads(block["text"])
                        except json.JSONDecodeError:
                            continue
                        if isinstance(value, dict) and "evidence_id" in value:
                            records.append(value)
        have = {record["system"] for record in records}
        missing = [name for name in ("procurement", "warehouse", "billing", "case_management") if name not in have]
        if missing:
            calls = [("observe_system", {"system": name}) for name in missing]
        elif "document:invoice" not in have or "document:delivery_note" not in have:
            calls = [("inspect_document", {"document": name}) for name in ("invoice", "delivery_note") if "document:" + name not in have]
        elif not any(block.get("name") == "record_hypotheses" for message in messages if isinstance(message.get("content"), list)
                     for block in message["content"]):
            calls = [("record_hypotheses", {"hypotheses": [{"claim": "Compare ordered, invoiced and confirmed received units before any business change.",
                       "assessment": "uncertain", "evidence_ids": [r["evidence_id"] for r in records[:3]]}]})]
        else:
            plan = await DiagnosticPlanner().propose([r for r in records if not r["system"].startswith("document:")])
            value = plan.model_dump(mode="json")
            value["evidence_ids"] += [r["evidence_id"] for r in records if r["system"].startswith("document:")]
            value["explanation"] = "Scripted integration proposal grounded in actual observed fixture records."
            submitted = any(block.get("name") == "submit_plan" for message in messages if isinstance(message.get("content"), list)
                            for block in message["content"])
            if self.incorrect_first and not submitted and value["actions"]:
                value["actions"][0]["amount"] += 1
            calls = [("submit_plan", value)]
        blocks = [{"type": "tool_use", "id": f"scripted-{round_number}-{i}", "name": name, "input": params}
                  for i, (name, params) in enumerate(calls)]
        return {"result": {"content": blocks, "stop_reason": "tool_use", "usage": {"input_tokens": 0, "output_tokens": 0}},
                "seconds": 0, "estimated_reserved_usd": 0}
