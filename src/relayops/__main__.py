"""Run the original synthetic workflow; live planning is explicitly gated."""
import argparse
import asyncio
import json
from pathlib import Path

from .environment import World, fixture
from .evaluator import evaluate
from .executor import approve, execute, reconcile
from .planner import AnthropicPlanner, DiagnosticPlanner
from .workflow import build_workflow


async def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    original = fixture(delivery_known=not args.unknown_delivery)
    world = World(args.output / "world.sqlite")
    world.initialize(original)
    planner = DiagnosticPlanner() if args.planner == "diagnostic" else AnthropicPlanner(
        world, json.loads(Path("data/pricing.json").read_text()))
    try:
        assessment = await build_workflow(world, planner).ainvoke({})
        plan = assessment["plan"]
        result = {"planner": planner.mode, "plan": plan.model_dump(mode="json"),
                  "simulation": assessment["simulation"], "activity": assessment["activity"],
                  "execution": "not authorized; no real-world connections"}
        if args.execute_sandbox and plan.actions:
            token = approve(world, plan, operator="explicit-cli-sandbox-demo")
            if args.inject_ack_loss:
                try:
                    execute(world, plan, token, timeout_after=0)
                except TimeoutError:
                    result["reconciled_unknown_actions"] = reconcile(world, plan, token)
            execute(world, plan, token)
            result["verification"] = evaluate(original, world.state(), world.events(), plan.outcome)
            result["execution"] = "synthetic sandbox only"
        result["final_state"] = world.state()
        result["events"] = world.events()
        result["live_model_generation"] = args.planner == "anthropic"
        if hasattr(planner, "metadata"):
            result["model"] = planner.metadata
        (args.output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"output": str(args.output), "planner": result["planner"], "outcome": plan.outcome,
                          "simulation_passed": result["simulation"]["passed"], "execution": result["execution"]}))
    finally:
        if hasattr(planner, "close"):
            await planner.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--planner", choices=("diagnostic", "anthropic"), default="diagnostic")
    parser.add_argument("--execute-sandbox", action="store_true")
    parser.add_argument("--inject-ack-loss", action="store_true")
    parser.add_argument("--unknown-delivery", action="store_true")
    args = parser.parse_args()
    if args.inject_ack_loss and not args.execute_sandbox:
        parser.error("--inject-ack-loss requires --execute-sandbox")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
