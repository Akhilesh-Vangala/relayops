import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from relayops.domain.models import Refused
from relayops.domain.environment import World
from relayops.domain.environment import fixture
from relayops.agents.planner import AnthropicPlanner
from relayops.agents.planner import DiagnosticPlanner


class Stream:
    def __init__(self, value=None, error=None):
        self.value, self.error = value, error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.error:
            raise self.error
        raise StopAsyncIteration

    async def get_final_message(self):
        return self.value


class SDK:
    def __init__(self, plan, *, tokens=200, error=None, stop="tool_use", model="claude-sonnet-5-5"):
        self.generation_calls = 0
        async def retrieve(name):
            return SimpleNamespace(id=name, lifecycle="active")
        async def count_tokens(**kwargs):
            return SimpleNamespace(input_tokens=tokens)
        def stream(**kwargs):
            self.generation_calls += 1
            value = SimpleNamespace(model=model, stop_reason=stop, content=[SimpleNamespace(type="tool_use", name="submit_plan", input=plan)],
                                    usage=SimpleNamespace(model_dump=lambda **kwargs: {"input_tokens": 200, "output_tokens": 100}))
            return Stream(value, error)
        self.models = SimpleNamespace(retrieve=retrieve)
        self.messages = SimpleNamespace(count_tokens=count_tokens, stream=stream)


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.world = World(Path(self.tmp.name) / "world.sqlite")
        self.world.initialize(fixture())
        self.observations = self.world.public_observations()
        self.plan = asyncio.run(DiagnosticPlanner().propose(self.observations)).model_dump(mode="json")
        self.pricing = {"model": "claude-sonnet-5-5", "input_per_million": 2, "output_per_million": 10}

    def test_typed_model_submission_and_no_second_paid_attempt(self):
        sdk = SDK(self.plan)
        planner = AnthropicPlanner(self.world, self.pricing, sdk=sdk)
        result = asyncio.run(planner.propose(self.observations))
        self.assertEqual(result.outcome, "resolve")
        with self.assertRaises(Refused):
            asyncio.run(planner.propose(self.observations))
        self.assertEqual(sdk.generation_calls, 1)

    def test_input_admission_rejects_before_generation(self):
        sdk = SDK(self.plan, tokens=8001)
        planner = AnthropicPlanner(self.world, self.pricing, sdk=sdk)
        with self.assertRaises(Refused):
            asyncio.run(planner.propose(self.observations))
        self.assertEqual(sdk.generation_calls, 0)

    def test_unknown_stream_retains_receipt_and_blocks_replay(self):
        sdk = SDK(self.plan, error=TimeoutError("scripted failure"))
        planner = AnthropicPlanner(self.world, self.pricing, sdk=sdk)
        with self.assertRaises(TimeoutError):
            asyncio.run(planner.propose(self.observations))
        with self.world.connect() as db:
            self.assertEqual(db.execute("SELECT status FROM model_calls").fetchone()[0], "unknown")
        with self.assertRaises(Refused):
            asyncio.run(planner.propose(self.observations))
        self.assertEqual(sdk.generation_calls, 1)

    def test_incomplete_submission_cannot_be_a_plan(self):
        planner = AnthropicPlanner(self.world, self.pricing, sdk=SDK(self.plan, stop="max_tokens"))
        with self.assertRaises(Refused):
            asyncio.run(planner.propose(self.observations))

    def test_pricing_admission_rejects_before_generation(self):
        sdk = SDK(self.plan)
        planner = AnthropicPlanner(self.world, {**self.pricing, "output_per_million": 1000}, sdk=sdk)
        with self.assertRaises(Refused):
            asyncio.run(planner.propose(self.observations))
        self.assertEqual(sdk.generation_calls, 0)

    def test_invalid_model_output_does_not_mutate_world(self):
        planner = AnthropicPlanner(self.world, self.pricing, sdk=SDK({"actions": []}))
        with self.assertRaises(ValueError):
            asyncio.run(planner.propose(self.observations))
        self.assertEqual(self.world.state(), fixture())
