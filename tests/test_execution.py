import asyncio
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import ValidationError

from relayops.domain import Action, Plan, Refused
from relayops.environment import World, fixture
from relayops.evaluator import evaluate
from relayops.executor import approve, execute, reconcile
from relayops.planner import DiagnosticPlanner
from relayops.policy import validate
from relayops.workflow import build_workflow


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.original = fixture()
        self.world = World(Path(self.tmp.name) / "world.sqlite")
        self.world.initialize(self.original)
        self.plan = asyncio.run(DiagnosticPlanner().propose(self.world.public_observations()))

    def test_graph_simulation_preserves_original(self):
        result = asyncio.run(build_workflow(self.world, DiagnosticPlanner()).ainvoke({}))
        self.assertTrue(result["simulation"]["passed"])
        self.assertEqual(self.world.state(), self.original)
        self.assertEqual(self.world.events(), [])

    def test_actual_business_effects_and_independent_verification(self):
        token = approve(self.world, self.plan, operator="test-operator")
        execute(self.world, self.plan, token)
        report = evaluate(self.original, self.world.state(), self.world.events(), self.plan.outcome)
        self.assertTrue(report["passed"])
        self.assertEqual(self.world.state()["billing"]["held_cents"], 50000)

    def test_unapproved_execution_has_no_effects(self):
        with self.assertRaises(Refused):
            execute(self.world, self.plan, "missing")
        self.assertEqual(self.world.state(), self.original)

    def test_exact_approved_proposal_required(self):
        token = approve(self.world, self.plan, operator="test-operator")
        edited = self.plan.model_copy(update={"explanation": "different reviewed proposal"})
        with self.assertRaises(Refused):
            execute(self.world, edited, token)
        self.assertEqual(self.world.state(), self.original)

    def test_wrong_amount_rejected(self):
        wrong = self.plan.model_copy(update={"actions": (Action(kind="hold_invoice", amount=49999), *self.plan.actions[1:])})
        with self.assertRaises(Refused):
            approve(self.world, wrong, operator="test-operator")

    def test_early_close_rejected(self):
        wrong = self.plan.model_copy(update={"actions": tuple(reversed(self.plan.actions))})
        with self.assertRaises(Refused):
            approve(self.world, wrong, operator="test-operator")

    def test_forged_evidence_rejected(self):
        wrong = self.plan.model_copy(update={"evidence_ids": ("fake", *self.plan.evidence_ids[1:])})
        with self.assertRaises(Refused):
            validate(self.world, wrong)

    def test_duplicate_evidence_rejected(self):
        wrong = self.plan.model_copy(update={"evidence_ids": (self.plan.evidence_ids[0],) * 4})
        with self.assertRaises(Refused):
            validate(self.world, wrong)

    def test_cross_tenant_scope_rejected(self):
        with self.assertRaises(Refused):
            self.world.observe("other-tenant", "billing")
        with self.assertRaises(Refused):
            approve(self.world, self.plan.model_copy(update={"tenant": "other-tenant"}), operator="test-operator")

    def test_stale_approval_blocked(self):
        token = approve(self.world, self.plan, operator="test-operator")
        self.world.change_source(received_units=90)
        with self.assertRaises(Refused):
            execute(self.world, self.plan, token)
        self.assertEqual(self.world.state()["billing"]["held_cents"], 0)

    def test_acknowledgement_loss_blocks_blind_retry(self):
        token = approve(self.world, self.plan, operator="test-operator")
        with self.assertRaises(TimeoutError):
            execute(self.world, self.plan, token, timeout_after=0)
        with self.assertRaises(Refused):
            execute(self.world, self.plan, token)
        self.assertEqual(self.world.state()["billing"]["held_cents"], 50000)
        self.assertEqual(self.world.state()["case_management"]["status"], "open")

    def test_new_process_state_handle_reconciles_without_duplicate(self):
        token = approve(self.world, self.plan, operator="test-operator")
        with self.assertRaises(TimeoutError):
            execute(self.world, self.plan, token, timeout_after=1)
        code = """import json,sys
from relayops.environment import World
from relayops.domain import Plan
from relayops.executor import reconcile,execute
value=json.load(sys.stdin)
world=World(value['path'])
plan=Plan.from_json(value['plan'])
assert reconcile(world,plan,value['approval'])==1
execute(world,plan,value['approval'])
"""
        subprocess.run([sys.executable, '-c', code], input=json.dumps({'path':str(self.world.path), 'plan':self.plan.model_dump(mode='json'), 'approval':token}), text=True, check=True)
        self.assertTrue(evaluate(self.original, self.world.state(), self.world.events(), "resolve")["passed"])

    def test_crash_between_actions_retains_partial_state(self):
        token = approve(self.world, self.plan, operator="test-operator")
        with self.assertRaises(InterruptedError):
            execute(self.world, self.plan, token, crash_before=2)
        self.assertEqual(self.world.state()["case_management"]["reserved_units"], 0)
        execute(World(self.world.path), self.plan, token)
        self.assertTrue(evaluate(self.original, self.world.state(), self.world.events(), "resolve")["passed"])

    def test_repeated_execution_idempotent(self):
        token = approve(self.world, self.plan, operator="test-operator")
        execute(self.world, self.plan, token)
        execute(self.world, self.plan, token)
        self.assertEqual(len([e for e in self.world.events() if e["kind"] == "action_applied"]), 4)

    def test_concurrent_same_plan_does_not_duplicate_effects(self):
        token = approve(self.world, self.plan, operator="test-operator")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: execute(World(self.world.path), self.plan, token), range(2)))
        self.assertEqual(len(results), 2)
        self.assertTrue(evaluate(self.original, self.world.state(), self.world.events(), "resolve")["passed"])

    def test_independent_evaluator_rejects_false_success(self):
        final = copy.deepcopy(self.original)
        final["case_management"]["status"] = "resolved"
        self.assertFalse(evaluate(self.original, final, [], "resolve")["passed"])

    def test_strict_action_schema_rejects_coercion_and_unknown_tools(self):
        for value in ({"kind": "hold_invoice", "amount": "500"}, {"kind": "send_email", "amount": 0},
                      {"kind": "hold_invoice", "amount": True}, {"kind": "hold_invoice", "amount": 10, "extra": 1}):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                Action.model_validate(value)

    def test_unknown_delivery_and_insufficient_stock_abstain(self):
        for index, overrides in enumerate(({'delivery_known': False}, {'stock': 3}, {'billed': 90})):
            with self.subTest(overrides=overrides):
                source = fixture(**overrides)
                world = World(Path(self.tmp.name) / f"uncertain-{index}.sqlite")
                world.initialize(source)
                result = asyncio.run(build_workflow(world, DiagnosticPlanner()).ainvoke({}))
                self.assertEqual(result["plan"].outcome, "needs_information")
                self.assertTrue(result["simulation"]["passed"])
                self.assertEqual(world.state(), source)

    def test_healthy_case_has_no_actions(self):
        source = fixture(received=100)
        world = World(Path(self.tmp.name) / "healthy.sqlite")
        world.initialize(source)
        result = asyncio.run(build_workflow(world, DiagnosticPlanner()).ainvoke({}))
        self.assertEqual(result["plan"].outcome, "no_change")
        self.assertEqual(result["plan"].actions, ())
        self.assertTrue(result["simulation"]["passed"])

    def test_varied_quantities_and_integer_currency(self):
        for index, (ordered, received, unit) in enumerate(((19, 7, 301), (1, 0, 1), (10000, 9990, 99999))):
            source = fixture(ordered=ordered, received=received, unit_cents=unit)
            world = World(Path(self.tmp.name) / f"variant-{index}.sqlite")
            world.initialize(source)
            plan = asyncio.run(DiagnosticPlanner().propose(world.public_observations()))
            token = approve(world, plan, operator="test-operator")
            execute(world, plan, token)
            self.assertTrue(evaluate(source, world.state(), world.events(), "resolve")["passed"])
