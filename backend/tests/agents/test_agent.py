import asyncio
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from relayops.agents.agent import investigate
from relayops.agents.agent import trim_images
from relayops.agents.browser import BrowserEvidence
from relayops.agents.browser import evidence_page
from relayops.domain.models import Refused
from relayops.domain.environment import World
from relayops.domain.environment import fixture
from relayops.agents.scripted_agent import ScriptedAgent


class AgentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.world = World(Path(self.tmp.name) / "world.sqlite")
        self.original = fixture()
        self.world.initialize(self.original)

    async def test_dynamic_observation_memory_and_correction(self):
        result = await investigate(self.world, ScriptedAgent(incorrect_first=True))
        self.assertEqual(result["rounds"], 5)
        self.assertEqual(result["tool_calls"], 6)
        self.assertEqual(result["corrections"], 1)
        self.assertEqual(len(result["evidence"]), 6)
        self.assertTrue(result["hypotheses"])
        self.assertEqual(self.world.state(), self.original)
        self.assertFalse(any(e["kind"] == "action_applied" for e in self.world.events()))

    async def test_explicit_checkpoint_recovery_preserves_budgets(self):
        with self.assertRaises(InterruptedError):
            await investigate(self.world, ScriptedAgent(interrupt_round=3))
        result = await investigate(self.world, ScriptedAgent(), recover=True)
        self.assertEqual(result["rounds"], 4)
        self.assertEqual(result["tool_calls"], 6)
        self.assertEqual(result["plan"]["outcome"], "resolve")

    async def test_completed_recovery_does_not_call_model(self):
        await investigate(self.world, ScriptedAgent())
        result = await investigate(self.world, ScriptedAgent(interrupt_round=1), recover=True)
        self.assertEqual(result["rounds"], 4)

    async def test_changed_source_blocks_recovery(self):
        await investigate(self.world, ScriptedAgent())
        self.world.change_source(received_units=90)
        with self.assertRaises(Refused):
            await investigate(self.world, ScriptedAgent(), recover=True)

    async def test_missing_information_is_grounded_and_nonmutating(self):
        world = World(Path(self.tmp.name) / "unknown" / "world.sqlite")
        original = fixture(delivery_known=False)
        world.initialize(original)
        result = await investigate(world, ScriptedAgent())
        self.assertEqual(result["plan"]["outcome"], "needs_information")
        self.assertEqual(result["plan"]["actions"], [])
        self.assertEqual(world.state(), original)

    async def test_repeated_calls_stop(self):
        class Looper(ScriptedAgent):
            async def complete(self, *args):
                round_number = args[3]
                return {"result": {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": str(round_number), "name": "observe_system", "input": {"system": "billing"}}],
                                   "usage": {"output_tokens": 0}}, "seconds": 0}
        with self.assertRaises(Refused):
            await investigate(self.world, Looper())

    async def test_forged_hypotheses_exhaust_correction_allowance(self):
        class Forger(ScriptedAgent):
            async def complete(self, *args):
                return {"result": {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": str(args[3]), "name": "record_hypotheses",
                              "input": {"hypotheses": [{"claim": "False", "assessment": "supported", "evidence_ids": ["invented"]}]}}],
                                   "usage": {"output_tokens": 0}}, "seconds": 0}
        with self.assertRaises(Refused):
            await investigate(self.world, Forger())

    async def test_unauthorized_tool_cannot_execute_writes(self):
        class Writer(ScriptedAgent):
            async def complete(self, *args):
                return {"result": {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": str(args[3]), "name": "execute", "input": {}}],
                                   "usage": {"output_tokens": 0}}, "seconds": 0}
        with self.assertRaises(Refused):
            await investigate(self.world, Writer())
        self.assertEqual(self.world.state(), self.original)

    async def test_real_browser_pixels_accessibility_and_hash(self):
        browser = BrowserEvidence(self.world)
        try:
            await browser.start()
            record, image = await browser.capture("document", "invoice", self.original["tenant"])
            self.assertIn("Supplier invoice", record["browser"]["accessibility"])
            self.assertEqual(image["source"]["media_type"], "image/png")
            path = self.world.path.parent / "observations" / (record["evidence_id"] + ".png")
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["browser"]["png_sha256"])
            with self.assertRaises(Refused):
                await browser.capture("document", "invoice", "other-tenant")
        finally:
            await browser.close()

    def test_image_context_prunes_old_pixels_without_changing_original(self):
        messages = [{"role": "user", "content": [{"type": "tool_result", "content": [{"type": "text", "text": "source"}, {"type": "image", "source": {"data": str(i)}}]}]} for i in range(5)]
        original = copy.deepcopy(messages)
        trimmed = trim_images(messages)
        self.assertEqual(sum(block["type"] == "image" for m in trimmed for r in m["content"] for block in r["content"]), 2)
        self.assertEqual(messages, original)

    def test_document_markup_is_escaped(self):
        with self.world.connect() as db:
            state = self.world.state(db)
            state["documents"]["invoice"]["note"] = '<script>alert("injection")</script>'
            db.execute("UPDATE state SET payload=? WHERE id=1", (json.dumps(state),))
        page = evidence_page(self.world, "document", "invoice")
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;', page)
