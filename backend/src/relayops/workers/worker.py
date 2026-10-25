"""Separate leased investigation worker; interrupted paid work is never replayed."""

import argparse
import asyncio
import json
import os
import signal
from pathlib import Path

from relayops.agents.agent import investigate
from relayops.agents.agent_transport import AgentModel
from relayops.agents.browser import BrowserEvidence
from relayops.domain.models import Plan
from relayops.domain.models import Refused
from relayops.domain.models import digest
from relayops.domain.environment import World
from relayops.domain.environment import fixture
from relayops.persistence.run_store import RunStore
from relayops.agents.scripted_agent import ScriptedAgent
from relayops.agents.workflow import simulate_plan
from relayops.product.run_contract import record

SCENARIO_OPTIONS = {
    "short-shipment": {},
    "unknown-delivery": {"delivery_known": False},
    "low-stock": {"stock": 3},
    "healthy-delivery": {"received": 100},
}


def heartbeat_file():
    path = Path(os.getenv("RELAY_WORKER_HEARTBEAT", "/tmp/relayops-worker-heartbeat"))
    temporary = path.with_suffix(".tmp")
    temporary.write_text(str(os.getpid()))
    temporary.replace(path)


async def run_job(store, job):
    browser = client = None
    world = World(store.root / "runs" / job["id"] / "world.sqlite")
    stop_heartbeat = asyncio.Event()
    task = asyncio.current_task()

    async def renew():
        while not stop_heartbeat.is_set():
            try:
                await asyncio.wait_for(stop_heartbeat.wait(), timeout=10)
            except asyncio.TimeoutError:
                try:
                    await asyncio.to_thread(store.heartbeat, job)
                    heartbeat_file()
                except Exception:
                    task.cancel()
                    return

    heartbeat = asyncio.create_task(renew())
    try:
        spec = job["spec"]
        world.initialize(
            fixture(name=spec["case_id"], **SCENARIO_OPTIONS[spec["case_id"]])
        )
        if spec["browser"]:
            browser = await BrowserEvidence(world).start()
        if spec["mode"] == "live":
            if os.getenv("RELAY_ALLOW_LIVE") != "1":
                raise Refused("Live worker admission is disabled")
            client = AgentModel(
                world,
                json.loads(
                    (
                        Path(__file__).resolve().parents[4]
                        / "backend/data/pricing.json"
                    ).read_text()
                ),
            )
        else:
            client = ScriptedAgent(incorrect_first=True)
        result = await investigate(world, client, browser=browser)
        result["simulation"] = await asyncio.to_thread(
            simulate_plan, world, Plan.from_json(result["plan"])
        )
        result["run_record"] = record(
            run_id=job["id"],
            task="case_resolution",
            mode=spec["mode"],
            owner_scope="operator-workspace",
            input_sha256=world.version(),
            contract={"task": "open-short-shipment", "version": "v1"},
            result={"plan": result["plan"], "simulation": result["simulation"]},
            verification_scope="independent-simulation",
            verification_passed=result["simulation"]["passed"],
            check_count=1,
            evidence_count=len(result["evidence"]),
            billing="unknown" if spec["mode"] == "live" else "not-used",
            producer_versions={
                "agent": result["agent_version"],
                "policy": "short-shipment-v1",
            },
        )
        result["version"] = digest(result)
        destination = world.path.parent / "assessment.json"
        temporary = destination.with_suffix("." + job["owner"] + ".tmp")
        temporary.write_text(json.dumps(result, indent=2) + "\n")
        await asyncio.to_thread(
            store.finish,
            job,
            "completed",
            publish=lambda: temporary.replace(destination),
        )
    except BaseException as error:
        terminal = (
            "interrupted" if isinstance(error, asyncio.CancelledError) else "failed"
        )
        try:
            await asyncio.to_thread(
                store.finish, job, terminal, error_kind=type(error).__name__
            )
        except Refused:
            pass  # Another worker expired the lease; the stale owner cannot publish.
        (world.path.parent / "failure.json").write_text(
            json.dumps({"kind": type(error).__name__, "status": terminal})
        )
        if isinstance(error, asyncio.CancelledError):
            raise
    finally:
        stop_heartbeat.set()
        await heartbeat
        if browser:
            await browser.close()
        if client and hasattr(client, "close"):
            await client.close()


async def run_one(store, identity=None):
    job = await asyncio.to_thread(store.claim, identity)
    if not job:
        return False
    await run_job(store, job)
    return True


async def serve(store, once=False):
    if once:
        return await run_one(store)
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    current = None

    def stop():
        stopping.set()
        if current:
            current.cancel()

    for number in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(number, stop)
    while not stopping.is_set():
        heartbeat_file()
        current = asyncio.create_task(run_one(store))
        try:
            worked = await current
        except asyncio.CancelledError:
            break
        finally:
            current = None
        if not worked:
            try:
                await asyncio.wait_for(stopping.wait(), timeout=0.5)
            except asyncio.TimeoutError:
                pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-dir",
        default=os.getenv("RELAY_STATE_DIR", "artifacts/generated/workbench"),
        type=Path,
    )
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    store = RunStore(args.state_dir)
    try:
        asyncio.run(serve(store, args.once))
    finally:
        store.close()


if __name__ == "__main__":
    main()
