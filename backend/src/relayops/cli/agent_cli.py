"""Run/recover a checkpointed investigation; defaults to explicitly scripted checks."""
import argparse
import asyncio
import json
from pathlib import Path

from relayops.agents.agent import investigate
from relayops.agents.agent_transport import AgentModel
from relayops.agents.browser import BrowserEvidence
from relayops.domain.models import Plan
from relayops.domain.environment import World
from relayops.domain.environment import fixture
from relayops.agents.scripted_agent import ScriptedAgent
from relayops.agents.workflow import simulate_plan


async def run(args):
    if not args.recover:
        args.output.mkdir(parents=True, exist_ok=False)
    world = World(args.output / "world.sqlite")
    if not args.recover:
        world.initialize(fixture(delivery_known=not args.unknown_delivery))
    client = (ScriptedAgent(incorrect_first=args.test_correction) if args.client == "scripted" else
              AgentModel(world, json.loads(Path("backend/data/pricing.json").read_text())))
    browser = BrowserEvidence(world) if args.browser else None
    try:
        if browser:
            await browser.start()
        report = await investigate(world, client, browser=browser, recover=args.recover)
        report["simulation"] = await asyncio.to_thread(simulate_plan, world, Plan.from_json(report["plan"]))
        (args.output / "assessment.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"client": report["client_mode"], "rounds": report["rounds"], "tools": report["tool_calls"],
                          "corrections": report["corrections"], "browser": report["browser_observations"],
                          "outcome": report["plan"]["outcome"], "simulation_passed": report["simulation"]["passed"]}))
    finally:
        if browser:
            await browser.close()
        if hasattr(client, "close"):
            await client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--client", choices=("scripted", "anthropic"), default="scripted")
    parser.add_argument("--browser", action="store_true")
    parser.add_argument("--recover", action="store_true")
    parser.add_argument("--test-correction", action="store_true")
    parser.add_argument("--unknown-delivery", action="store_true")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
