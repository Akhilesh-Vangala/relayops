import json
import tempfile
import unittest
from pathlib import Path

import httpx2
from anthropic import AsyncAnthropic

from relayops.agent_transport import AgentModel
from relayops.domain import Refused
from relayops.environment import World, fixture


def stream_response(round_number=1, *, incomplete=False):
    events = [
        ("message_start", {"type": "message_start", "message": {"id": "msg-test", "type": "message", "role": "assistant", "model": "claude-sonnet-5-5", "content": [], "stop_reason": None,
                       "stop_sequence": None, "usage": {"input_tokens": 120, "output_tokens": 0}}}),
        ("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": f"call-{round_number}", "name": "observe_system", "input": {}}}),
        ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": '{"system":"warehouse"}'}}),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "tool_use", "stop_sequence": None}, "usage": {"output_tokens": 30}}),
        ("message_stop", {"type": "message_stop"}),
    ]
    if incomplete:
        events = events[:2]
    return ''.join(f'event: {name}\ndata: {json.dumps(value)}\n\n' for name, value in events)


class TransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.world = World(Path(self.tmp.name) / "world.sqlite")
        self.world.initialize(fixture())
        self.requests = []
        self.status = 200
        self.input_count = 120
        self.incomplete = False
        self.profile = {"model": "claude-sonnet-5-5", "input_per_million": 2, "output_per_million": 10}

    def client(self):
        def handler(request):
            self.requests.append(request)
            if request.method == 'GET':
                return httpx2.Response(200, json={"id": "claude-sonnet-5-5", "type": "model", "display_name": "Test model",
                                                 "created_at": "2026-01-01T00:00:00Z", "lifecycle": "active"})
            if request.url.path.endswith('count_tokens'):
                return httpx2.Response(200, json={"input_tokens": self.input_count})
            if self.status != 200:
                return httpx2.Response(self.status, json={"type": "error", "error": {"type": "rate_limit_error", "message": "test"}})
            return httpx2.Response(200, headers={'content-type':'text/event-stream'}, text=stream_response(incomplete=self.incomplete))
        sdk = AsyncAnthropic(api_key="test-only", base_url="https://mock.invalid", max_retries=0,
                             http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)), _strict_response_validation=True)
        return AgentModel(self.world, self.profile, sdk=sdk)

    async def test_actual_sdk_http_sse_and_receipt_replay(self):
        client = self.client()
        try:
            result = await client.complete("test", [{"role":"user","content":"observe"}], [], 1, 2048)
            self.assertEqual(result['result']['content'][0]['input'], {'system':'warehouse'})
            again = await client.complete("test", [{"role":"user","content":"observe"}], [], 1, 2048)
            self.assertEqual(result, again)
            self.assertEqual(sum(r.url.path == '/v1/messages' for r in self.requests), 1)
            self.assertGreater(result['reported_cost_estimate_usd'], 0)
        finally:
            await client.close()

    async def test_rate_limit_unknown_receipt_no_retries_or_replay(self):
        self.status = 429
        client = self.client()
        try:
            with self.assertRaises(Exception):
                await client.complete("test", [], [], 1, 2048)
            with self.assertRaises(Refused):
                await client.complete("test", [], [], 1, 2048)
            self.assertEqual(sum(r.url.path == '/v1/messages' for r in self.requests), 1)
            with self.world.connect() as db:
                self.assertEqual(db.execute('SELECT status FROM agent_model_calls').fetchone()[0], 'unknown')
        finally:
            await client.close()

    async def test_input_admission_blocks_generation(self):
        self.input_count = 8001
        client = self.client()
        try:
            with self.assertRaises(Refused):
                await client.complete("test", [], [], 1, 2048)
            self.assertFalse(any(r.url.path == '/v1/messages' for r in self.requests))
        finally:
            await client.close()

    async def test_changed_request_cannot_reuse_completed_receipt(self):
        client = self.client()
        try:
            await client.complete("test", [], [], 1, 2048)
            with self.assertRaises(Refused):
                await client.complete("changed", [], [], 1, 2048)
        finally:
            await client.close()

    async def test_partial_stream_is_not_a_completed_result(self):
        self.incomplete = True
        client = self.client()
        try:
            with self.assertRaises(Exception):
                await client.complete("test", [], [], 1, 2048)
        finally:
            await client.close()
