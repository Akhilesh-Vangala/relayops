"""Bounded streaming model rounds with persistent result receipts and admission."""

import asyncio
import json
import os
import time
from decimal import Decimal
from decimal import ROUND_CEILING

from relayops.domain.models import Refused
from relayops.domain.models import digest


class AgentModel:
    mode = "live-tool-using-model"

    def __init__(self, world, pricing, *, sdk=None):
        from anthropic import AsyncAnthropic

        if sdk is None and (
            os.getenv("RELAY_ALLOW_LIVE") != "1"
            or not os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("RELAY_MODEL") != pricing["model"]
        ):
            raise Refused(
                "Live agent requires explicit private key/model/RELAY_ALLOW_LIVE=1 configuration"
            )
        self.sdk = sdk or AsyncAnthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            max_retries=0,
            timeout=30,
            _strict_response_validation=True,
        )
        self.world, self.pricing, self.resolved = world, pricing, None
        with world.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS agent_model_calls (round INTEGER PRIMARY KEY, request_hash TEXT NOT NULL, status TEXT NOT NULL, estimate_micro INTEGER NOT NULL, input_count INTEGER NOT NULL, payload TEXT)"
            )

    async def complete(self, system, messages, tools, round_number, max_tokens):
        model = self.pricing["model"]
        request = {
            "model": model,
            "system": system,
            "messages": messages,
            "tools": tools,
            "max_tokens": max_tokens,
        }
        encoded = json.dumps(request)
        if len(encoded.encode()) > 2_000_000:
            raise Refused("Model body exceeds the multimodal byte allowance")
        request_hash = digest(request)
        with self.world.connect() as db:
            previous = db.execute(
                "SELECT * FROM agent_model_calls WHERE round=?", (round_number,)
            ).fetchone()
            if previous:
                if (
                    previous["request_hash"] != request_hash
                    or previous["status"] != "completed"
                ):
                    raise Refused("Changed or uncertain model receipt blocks replay")
                return json.loads(previous["payload"])
            if db.execute(
                "SELECT 1 FROM agent_model_calls WHERE status!='completed'"
            ).fetchone():
                raise Refused(
                    "Uncertain prior generation requires billing reconciliation"
                )
        if not self.resolved:
            info = await self.sdk.models.retrieve(model)
            if info.id != model or info.lifecycle != "active":
                raise Refused("Trusted pricing must match the active resolved model")
            self.resolved = info.id
        counted = await self.sdk.messages.count_tokens(
            model=model, system=system, messages=messages, tools=tools
        )
        if (
            type(counted.input_tokens) is not int
            or not 0 <= counted.input_tokens <= 8000
        ):
            raise Refused("Input context allowance exceeded")
        estimate = int(
            (
                Decimal(counted.input_tokens)
                * Decimal(str(self.pricing["input_per_million"]))
                + Decimal(max_tokens) * Decimal(str(self.pricing["output_per_million"]))
            ).to_integral_value(rounding=ROUND_CEILING)
        )
        if estimate < 0:
            raise Refused("Invalid pricing profile")
        with self.world.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            used = db.execute(
                "SELECT COALESCE(SUM(estimate_micro),0),COALESCE(SUM(input_count),0) FROM agent_model_calls"
            ).fetchone()
            if used[0] + estimate > 500000 or used[1] + counted.input_tokens > 64000:
                raise Refused("Cumulative cost/context allowance exhausted")
            if (
                db.execute(
                    "SELECT 1 FROM sqlite_master WHERE name='model_calls'"
                ).fetchone()
                and db.execute("SELECT 1 FROM model_calls").fetchone()
            ):
                raise Refused("Legacy model receipts cannot be mixed with agent rounds")
            db.execute(
                "INSERT INTO agent_model_calls VALUES (?,?,?,?,?,NULL)",
                (
                    round_number,
                    request_hash,
                    "reserved",
                    estimate,
                    counted.input_tokens,
                ),
            )
        started = time.monotonic()
        try:
            finished = False
            async with asyncio.timeout(60):
                async with self.sdk.messages.stream(**request) as stream:
                    async for event in stream:
                        if event.type == "message_stop":
                            finished = True
                    message = await stream.get_final_message()
            if not finished:
                raise Refused("Incomplete provider stream; billing remains uncertain")
            result = message.model_dump(mode="json", exclude_none=True)
            if result.get("model") != model:
                raise Refused("Unexpected billed response model")
            usage = result.get("usage", {})
            if any(
                type(usage.get(key)) is not int or usage[key] < 0
                for key in ("input_tokens", "output_tokens")
            ):
                raise Refused("Complete nonnegative usage is required")
            if usage.get("cache_creation_input_tokens", 0) or usage.get(
                "cache_read_input_tokens", 0
            ):
                raise Refused(
                    "Unexpected cache billing requires explicit pricing reconciliation"
                )
            actual = int(
                (
                    Decimal(usage["input_tokens"])
                    * Decimal(str(self.pricing["input_per_million"]))
                    + Decimal(usage["output_tokens"])
                    * Decimal(str(self.pricing["output_per_million"]))
                ).to_integral_value(rounding=ROUND_CEILING)
            )
            payload = {
                "result": result,
                "seconds": time.monotonic() - started,
                "estimated_reserved_usd": estimate / 1_000_000,
                "reported_cost_estimate_usd": actual / 1_000_000,
            }
            with self.world.connect() as db:
                db.execute(
                    "UPDATE agent_model_calls SET status='completed',payload=?,estimate_micro=? WHERE round=?",
                    (json.dumps(payload), max(estimate, actual), round_number),
                )
            return payload
        except BaseException:
            with self.world.connect() as db:
                db.execute(
                    "UPDATE agent_model_calls SET status='unknown' WHERE round=? AND status='reserved'",
                    (round_number,),
                )
            raise

    async def close(self):
        await self.sdk.close()
