"""Actual local browser/agent/operator journey in an isolated synthetic workspace."""
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
output=root/'artifacts/generated'/('browser-workbench-'+uuid.uuid4().hex[:8])
output.mkdir(parents=True)
with socket.socket() as sock:
    sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
env=dict(os.environ,PYTHONPATH=str(root/'src'),RELAY_ALLOW_LIVE='0')
env.pop('ANTHROPIC_API_KEY',None)
log=(output/'server.log').open('w')
server=subprocess.Popen([sys.executable,'-m','relayops.web','--port',str(port),'--state-dir',str(output/'state')],cwd=root,env=env,stdout=log,stderr=log)
checks=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1440,'height':1000})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        for _ in range(80):
            try:
                response=page.request.get(f'http://127.0.0.1:{port}/')
                if response.ok:break
            except Exception:pass
            time.sleep(.1)
        else:raise RuntimeError('Server did not start')
        base=f'http://127.0.0.1:{port}'
        page.goto(base)
        assert page.get_by_role('heading',name='Resolve exceptions. Verify every change.').is_visible()
        checks.append('home actual configuration and case cards')
        page.get_by_role('link',name='Short shipment').first.click()
        assert page.locator('#mode option[value=live]').is_disabled()
        checks.append('live option disabled without private configuration')
        page.get_by_role('button',name='Investigate with browser evidence').click()
        page.wait_for_url('**/runs/*')
        page.get_by_role('heading',name='Proposed business actions').wait_for(timeout=45000)
        identity=page.url.rsplit('/',1)[1]
        api=page.request.get(base+'/api/runs/'+identity).json()
        report=api['assessment']
        assert report['client_mode']=='scripted-agent-integration' and report['rounds']==5 and report['tool_calls']==6 and report['corrections']==1
        assert report['simulation']['passed']
        checks.append('actual tool loop, correction and independent simulation')
        assert len(report['evidence'])==6 and all(record.get('browser') for record in report['evidence'])
        checks.append('six actual screenshots and accessibility observations')
        page.reload()
        assert page.get_by_role('heading',name='Public hypothesis memory').is_visible()
        checks.append('detail deep link and reload')
        page.locator('details').first.locator('summary').click()
        assert page.locator('details').first.locator('img').is_visible()
        checks.append('grounded source screenshot viewer')
        page.evaluate('scrollTo(0,0)')
        page.screenshot(path=str(output/'desktop-investigation.png'),full_page=True)
        stale=page.request.post(base+'/api/runs/'+identity+'/review',data={'version':'stale','action':'approve'})
        assert stale.status==409
        checks.append('stale version review rejected server-side')
        denied=page.request.post(base+'/api/runs/'+identity+'/execute',data={'version':report['version']})
        assert denied.status==409
        checks.append('execution before approval blocked')
        page.get_by_role('button',name='Approve sandbox proposal').click()
        page.get_by_role('button',name='Execute approved sandbox actions').wait_for()
        duplicate=page.request.post(base+'/api/runs/'+identity+'/review',data={'version':report['version'],'action':'reject'})
        assert duplicate.status==409
        checks.append('immutable exact-version review')
        page.get_by_role('button',name='Execute approved sandbox actions').click()
        page.get_by_role('heading',name='Execution verification').wait_for()
        execution=page.request.post(base+'/api/runs/'+identity+'/execute',data={'version':report['version']}).json()
        assert execution['passed'] and execution['checks']['no_duplicate_effects']
        checks.append('approved execution and repeated request without duplicate effects')
        for width in [320,390,768,1440]:
            page.set_viewport_size({'width':width,'height':900})
            for path in ['/','/cases','/runs','/architecture','/runs/'+identity]:
                page.goto(base+path)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,path)
                colored=page.evaluate('''()=>[...document.querySelectorAll('*')].some(e=>{const m=getComputedStyle(e).color.match(/rgba?\\((\\d+), (\\d+), (\\d+)/);return m&&!(m[1]===m[2]&&m[2]===m[3]);})''')
                assert not colored,(width,path)
            checks.append(f'five pages responsive monochrome at {width}px')
        page.set_viewport_size({'width':390,'height':844});page.goto(base+'/runs/'+identity)
        page.screenshot(path=str(output/'mobile-investigation.png'),full_page=True)
        page.goto(base+'/cases/unknown-delivery')
        page.get_by_role('button',name='Investigate with browser evidence').click()
        page.wait_for_url('**/runs/*');page.get_by_role('heading',name='Proposed business actions').wait_for(timeout=45000)
        value=page.request.get(base+'/api/runs/'+page.url.rsplit('/',1)[1]).json()['assessment']
        assert value['plan']['outcome']=='needs_information' and not value['plan']['actions']
        assert page.get_by_role('button',name='Approve sandbox proposal').count()==0
        checks.append('unknown delivery produces grounded no-write clarification')
        assert not errors,errors
        checks.append('no browser runtime errors')
        (output/'result.json').write_text(json.dumps({'passed':True,'checks':checks,'live_model_generation':False,'run_id':identity},indent=2)+'\n')
        print(json.dumps({'output':str(output),'checks':len(checks),'passed':True}))
        browser.close()
finally:
    server.terminate()
    try:server.wait(timeout=10)
    except subprocess.TimeoutExpired:server.kill();server.wait()
    log.close()
