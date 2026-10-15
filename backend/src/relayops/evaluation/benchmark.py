"""Known development workflow matrix; no live capability or held-out claims."""
import argparse
import asyncio
import json
from pathlib import Path

from relayops.agents.agent import investigate
from relayops.domain.models import Plan
from relayops.domain.models import digest
from relayops.domain.environment import World
from relayops.domain.environment import fixture
from relayops.agents.scripted_agent import ScriptedAgent
from relayops.agents.workflow import simulate_plan

CASES = [
    ("short-default", {}), ("short-small", {"ordered":19,"received":7,"unit_cents":301}),
    ("short-one", {"ordered":1,"received":0,"unit_cents":1}), ("short-large", {"ordered":10000,"received":9990,"unit_cents":99999}),
    ("missing-delivery", {"delivery_known":False}), ("low-stock", {"stock":3}),
    ("invoice-disagreement", {"billed":90}), ("healthy-default", {"received":100}),
    ("healthy-small", {"ordered":4,"received":4}), ("healthy-empty", {"ordered":0,"received":0}),
    ("short-stock-boundary", {"stock":20}), ("missing-delivery-and-stock", {"delivery_known":False,"stock":0}),
]


async def run(output):
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for name, parameters in CASES:
        world = World(output / name / "world.sqlite")
        original = fixture(name=name, **parameters)
        world.initialize(original)
        report = await investigate(world, ScriptedAgent(incorrect_first=True))
        simulation = simulate_plan(world, Plan.from_json(report['plan']))
        records.append({"case":name,"outcome":report['plan']['outcome'],"assessment_passed":simulation['passed'],
                        "original_business_untouched":world.state()==original,"rounds":report['rounds'],
                        "tool_calls":report['tool_calls'],"corrections":report['corrections']})
    result = {"scope":"Known original synthetic development workflows with scripted model choices; not unseen or live-model accuracy",
              "manifest_sha256":digest(CASES),"client":"scripted-agent-integration","cases":records,
              "passing_assessments":sum(r['assessment_passed'] and r['original_business_untouched'] for r in records),
              "case_count":len(records),"live_model_generations":0}
    (output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['case_count','passing_assessments','live_model_generations']}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    asyncio.run(run(parser.parse_args().output))


if __name__=='__main__':
    main()
