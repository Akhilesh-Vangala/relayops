"""Actual LangGraph assessment workflow; approval and execution stay outside it."""
import tempfile
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .domain import Refused
from .environment import World
from .evaluator import evaluate
from .executor import approve, execute
from .policy import validate


class State(TypedDict, total=False):
    observations: list
    plan: dict
    policy: str
    simulation: dict
    activity: list


def simulate_plan(world, plan):
    original = world.state()
    with tempfile.TemporaryDirectory(prefix="relayops-simulation-") as directory:
        shadow = World(Path(directory) / "world.sqlite")
        shadow.initialize(original)
        with world.connect() as source, shadow.connect() as destination:
            for row in source.execute("SELECT * FROM evidence"):
                destination.execute("INSERT INTO evidence VALUES (?,?,?,?,?)", tuple(row))
        if plan.actions:
            token = approve(shadow, plan, operator="counterfactual-simulator")
            execute(shadow, plan, token)
        report = evaluate(original, shadow.state(), shadow.events(), plan.outcome)
        if not report["passed"]:
            raise Refused("Counterfactual final state failed independent checks")
    return report


def build_workflow(world, planner):
    def observe(state):
        return {"observations": world.public_observations(), "activity": ["observed-four-systems"]}

    async def propose(state):
        plan = await planner.propose(state["observations"])
        return {"plan": plan, "activity": state["activity"] + ["proposed-plan"]}

    def policy(state):
        validate(world, state["plan"])
        return {"policy": "passed", "activity": state["activity"] + ["policy-validated"]}

    def simulate(state):
        report = simulate_plan(world, state["plan"])
        return {"simulation": report, "activity": state["activity"] + ["simulated-on-private-copy", "awaiting-operator-if-actions"]}

    builder = StateGraph(State)
    for name, node in (("observe", observe), ("propose", propose), ("policy", policy), ("simulate", simulate)):
        builder.add_node(name, node)
    builder.add_edge(START, "observe")
    builder.add_edge("observe", "propose")
    builder.add_edge("propose", "policy")
    builder.add_edge("policy", "simulate")
    builder.add_edge("simulate", END)
    return builder.compile()
