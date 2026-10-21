"""Injected provider corruption cannot bypass persistent workflow budgets."""
import tempfile
import unittest
from pathlib import Path
from relayops.agents.agent import investigate
from relayops.agents.scripted_agent import ScriptedAgent
from relayops.domain.environment import World,fixture
from relayops.domain.models import Refused

class ProviderBoundaryTests(unittest.IsolatedAsyncioTestCase):
 async def test_malformed_usage_time_and_names_are_refused_without_actions(self):
  cases=[None,{}, {"result":{} ,"seconds":float("nan")},{"result":{},"seconds":-1},{"result":{},"seconds":True}]
  good={"stop_reason":"tool_use","content":[{"type":"tool_use","id":"one","name":"observe_system","input":{"system":"billing"}}]}
  for usage in [None,{}, {"output_tokens":True},{"output_tokens":-1}]:
   cases.append({"result":{**good,"usage":usage},"seconds":0})
  cases.append({"result":{**good,"usage":{"output_tokens":0},"content":[{"type":"tool_use","id":"one","name":[],"input":{}}]},"seconds":0})
  for payload in cases:
   with self.subTest(payload=payload),tempfile.TemporaryDirectory() as tmp:
    world=World(Path(tmp)/"world.sqlite");original=fixture();world.initialize(original)
    class Corrupted(ScriptedAgent):
     async def complete(self,*args): return payload
    with self.assertRaises(Refused): await investigate(world,Corrupted())
    self.assertEqual(world.state(),original)
    self.assertFalse(any(e["kind"]=="action_applied" for e in world.events()))
