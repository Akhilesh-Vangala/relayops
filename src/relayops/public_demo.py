"""Request-bounded synthetic workflow using the actual planner/policy/executor.

Signed browser envelopes carry scope, never arbitrary business state. Each HTTP
action reconstructs a fresh fixture. This is not the durable worker deployment.
"""

import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import tempfile
from typing import Literal
import uuid

from fastapi import HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from .demo_security import DemoSession
from .domain import Refused, digest
from .environment import World
from .evaluator import evaluate
from .executor import approve, execute, reconcile
from .planner import DiagnosticPlanner
from .workflow import build_workflow

ASSETS = Path(__file__).parent / "demo_assets"
WRITE_PATHS = {
    "/api/demo/investigate",
    "/api/demo/review",
    "/api/demo/execute",
    "/api/demo/reconcile",
}


class Start(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    case_id: Literal[
        "short-shipment", "unknown-delivery", "low-stock", "healthy-delivery"
    ]


class Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    token: str = Field(min_length=1, max_length=18000)


class Review(Envelope):
    action: Literal["approve", "reject"]


class Execute(Envelope):
    failure_mode: Literal["none", "acknowledgment_loss"] = "none"


def attach(app, scenarios):
    from .environment import fixture

    session = DemoSession(
        os.environ.get("RELAY_DEMO_SECRET", ""), "relayops_demo_session"
    )

    @asynccontextmanager
    async def assessment(case_id):
        if case_id not in scenarios:
            raise HTTPException(404, "Unknown sandbox case")
        original = fixture(name=case_id, **scenarios[case_id][2])
        with tempfile.TemporaryDirectory(prefix="relayops-public-demo-") as directory:
            world = World(Path(directory) / "world.sqlite")
            world.initialize(original)
            state = await build_workflow(world, DiagnosticPlanner()).ainvoke({})
            proposal = {
                "case_id": case_id,
                "plan": state["plan"].model_dump(mode="json"),
                "simulation": state["simulation"],
                "source_version": world.version(),
            }
            proposal["version"] = digest(proposal)
            yield world, original, state, proposal

    def check(state, proposal, stage):
        if state.get("version") != proposal["version"]:
            raise HTTPException(409, "Source or proposal changed; investigate again")
        if state.get("stage") != stage:
            raise HTTPException(
                409, "This action requires the current " + stage + " state"
            )

    def publish(
        request, saved, world, original, state, proposal, stage, execution=None
    ):
        saved = {**saved, "version": proposal["version"], "stage": stage}
        observations = state["observations"]
        with world.connect() as db:
            receipts = [
                dict(row)
                for row in db.execute(
                    "SELECT action_index,status,payload FROM receipts ORDER BY action_index"
                )
            ]
        return {
            "id": saved["id"],
            "case_id": saved["case_id"],
            "title": scenarios[saved["case_id"]][0],
            "stage": stage,
            "version": proposal["version"],
            "token": session.issue(saved, session.visitor(request)),
            "mode": "Guided diagnostic · no model calls",
            "plan": proposal["plan"],
            "simulation": proposal["simulation"],
            "execution": execution,
            "before": original,
            "after": world.state(),
            "evidence": observations,
            "activity": state["activity"],
            "events": world.events(),
            "receipts": receipts,
            "scope": "Synthetic per-request sandbox. Replays reconstruct an isolated fixture; durable cross-request effects require the private worker deployment.",
        }

    @app.get("/api/demo/config")
    def config(request: Request, response: Response):
        session.visitor(request, response)
        return {
            "project": "RelayOps",
            "interactive": True,
            "mode": "guided",
            "live_model": False,
            "history": "this browser session",
            "cases": [
                {"id": key, "title": v[0], "description": v[1]}
                for key, v in scenarios.items()
            ],
        }

    @app.post("/api/demo/investigate")
    async def investigate(body: Start, request: Request):
        session.visitor(request)
        async with assessment(body.case_id) as (world, original, state, proposal):
            saved = {"id": uuid.uuid4().hex, "case_id": body.case_id}
            return publish(request, saved, world, original, state, proposal, "assessed")

    @app.post("/api/demo/review")
    async def review(body: Review, request: Request):
        saved = session.consume(request, body.token)
        async with assessment(saved["case_id"]) as (world, original, state, proposal):
            check(saved, proposal, "assessed")
            if not state["plan"].actions or not state["simulation"]["passed"]:
                raise HTTPException(
                    409, "No verified actions are available for approval"
                )
            return publish(
                request,
                saved,
                world,
                original,
                state,
                proposal,
                "approved" if body.action == "approve" else "rejected",
            )

    @app.post("/api/demo/execute")
    async def apply(body: Execute, request: Request):
        saved = session.consume(request, body.token)
        async with assessment(saved["case_id"]) as (world, original, state, proposal):
            check(saved, proposal, "approved")
            approval = await asyncio.to_thread(
                approve, world, state["plan"], operator="anonymous-sandbox-review"
            )
            try:
                await asyncio.to_thread(
                    execute,
                    world,
                    state["plan"],
                    approval,
                    timeout_after=0
                    if body.failure_mode == "acknowledgment_loss"
                    else None,
                )
            except TimeoutError:
                return publish(
                    request, saved, world, original, state, proposal, "uncertain"
                )
            result = evaluate(
                original, world.state(), world.events(), state["plan"].outcome
            )
            first_state, first_events = world.state(), world.events()
            await asyncio.to_thread(execute, world, state["plan"], approval)
            result["same_request_retry_no_duplicates"] = (
                world.state() == first_state and world.events() == first_events
            )
            return publish(
                request, saved, world, original, state, proposal, "executed", result
            )

    @app.post("/api/demo/reconcile")
    async def recover(body: Envelope, request: Request):
        saved = session.consume(request, body.token)
        async with assessment(saved["case_id"]) as (world, original, state, proposal):
            check(saved, proposal, "uncertain")
            approval = await asyncio.to_thread(
                approve, world, state["plan"], operator="anonymous-sandbox-review"
            )
            try:
                await asyncio.to_thread(
                    execute, world, state["plan"], approval, timeout_after=0
                )
            except TimeoutError:
                pass
            recovered = await asyncio.to_thread(
                reconcile, world, state["plan"], approval
            )
            await asyncio.to_thread(execute, world, state["plan"], approval)
            result = evaluate(
                original, world.state(), world.events(), state["plan"].outcome
            )
            result["reconciled_receipts"] = recovered
            return publish(
                request, saved, world, original, state, proposal, "executed", result
            )

    @app.get("/demo/recording")
    @app.get("/demo")
    @app.get("/demo/runs/{identity}")
    def index(identity: str = ""):
        return FileResponse(ASSETS / "index.html")

    @app.get("/demo-assets/{name}")
    def assets(name: Literal["app.js", "style.css", "walkthrough.webm", "poster.png"]):
        return FileResponse(ASSETS / name)

    @app.get("/api/demo/runs")
    def history():
        return []

    @app.get("/api/demo/runs/{identity}")
    def detail(identity: str):
        raise HTTPException(
            404, "Demo results are retained only in their browser session"
        )

    @app.exception_handler(Refused)
    async def refused(request, error):
        return Response(
            json.dumps({"detail": str(error)}),
            status_code=409,
            media_type="application/json",
        )
