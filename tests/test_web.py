import asyncio
import json
import tempfile
import unittest
from pathlib import Path

import httpx

from relayops.domain import digest
from relayops.environment import World
from relayops.web import create_app


class WebTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.app = create_app(self.root)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app,client=('127.0.0.1',1)),base_url='http://localhost')

    async def asyncTearDown(self):
        await self.client.aclose()

    async def completed(self):
        response = await self.client.post('/api/runs',json={'case_id':'short-shipment','browser':False},headers={'Idempotency-Key':'first'})
        self.assertEqual(response.status_code,200)
        identity=response.json()['id']
        for _ in range(200):
            status=(await self.client.get('/api/runs/'+identity)).json()
            if status['status'] not in ('queued','running'):break
            await asyncio.sleep(.02)
        self.assertEqual(status['status'],'completed',status)
        return identity,status['assessment']

    async def test_idempotency_reuses_one_run_and_conflicts_on_changed_request(self):
        identity,report=await self.completed()
        again=await self.client.post('/api/runs',json={'case_id':'short-shipment','browser':False},headers={'Idempotency-Key':'first'})
        self.assertEqual(again.json()['id'],identity)
        changed=await self.client.post('/api/runs',json={'case_id':'unknown-delivery','browser':False},headers={'Idempotency-Key':'first'})
        self.assertEqual(changed.status_code,409)

    async def test_review_integrity_immutability_and_duplicate_execution(self):
        identity,report=await self.completed()
        version=report['version']
        before=await self.client.post('/api/runs/'+identity+'/execute',json={'version':version})
        self.assertEqual(before.status_code,409)
        reviewed=await self.client.post('/api/runs/'+identity+'/review',json={'version':version,'action':'approve'})
        self.assertEqual(reviewed.status_code,200)
        duplicate=await self.client.post('/api/runs/'+identity+'/review',json={'version':version,'action':'reject'})
        self.assertEqual(duplicate.status_code,409)
        for _ in range(2):
            execution=await self.client.post('/api/runs/'+identity+'/execute',json={'version':version})
            self.assertTrue(execution.json()['passed'])
        world=World(self.root/'runs'/identity/'world.sqlite')
        self.assertEqual(len([e for e in world.events() if e['kind']=='action_applied']),4)

    async def test_tampered_report_cannot_be_reviewed(self):
        identity,report=await self.completed()
        report['plan']['explanation']='changed stored result'
        (self.root/'runs'/identity/'assessment.json').write_text(json.dumps(report))
        response=await self.client.post('/api/runs/'+identity+'/review',json={'version':report['version'],'action':'approve'})
        self.assertEqual(response.status_code,409)

    async def test_changed_source_blocks_review_and_execution(self):
        identity,report=await self.completed()
        world=World(self.root/'runs'/identity/'world.sqlite')
        world.change_source(received_units=90)
        response=await self.client.post('/api/runs/'+identity+'/review',json={'version':report['version'],'action':'approve'})
        self.assertEqual(response.status_code,409)
        self.assertEqual(world.state()['billing']['held_cents'],0)

    async def test_request_schema_paths_host_origin_and_csp(self):
        self.assertEqual((await self.client.get('/runs/not-a-run')).status_code,404)
        response=await self.client.post('/api/runs',json={'case_id':'short-shipment','path':'/etc/passwd'},headers={'Idempotency-Key':'bad'})
        self.assertEqual(response.status_code,422)
        response=await self.client.post('/api/runs',json={'case_id':'short-shipment'},headers={'Idempotency-Key':'bad','Origin':'https://evil.invalid'})
        self.assertEqual(response.status_code,403)
        self.assertEqual((await self.client.get('/',headers={'Host':'evil.invalid'})).status_code,403)
        response=await self.client.get('/')
        self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
        self.assertEqual(response.headers['Cache-Control'],'no-store')
