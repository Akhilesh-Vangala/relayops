"""Local monochrome operator workbench; synthetic worlds, separate run records."""
import asyncio
import hashlib
import base64
import secrets
import html
import json
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.responses import Response
from fastapi.responses import RedirectResponse
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pydantic import ConfigDict

from relayops.agents.agent import fingerprint
from relayops.agents.browser import evidence_page
from relayops.domain.models import Plan
from relayops.domain.models import Refused
from relayops.domain.models import digest
from relayops.domain.environment import World
from relayops.domain.environment import fixture
from relayops.verification.evaluator import evaluate
from relayops.execution.executor import approve
from relayops.execution.executor import execute
from relayops.persistence.run_store import RunStore
from relayops.workers.worker import run_one

SCENARIOS = {
    "short-shipment": ("Short shipment", "100 ordered · 80 confirmed delivered · reconcile 20 missing units", {}),
    "unknown-delivery": ("Unconfirmed delivery", "Missing authoritative confirmation · clarification required", {"delivery_known": False}),
    "low-stock": ("Insufficient replacement stock", "20 units missing · only 3 replacement units available", {"stock": 3}),
    "healthy-delivery": ("Healthy delivery", "All 100 units delivered · verify no change is needed", {"received": 100}),
}
CSS = (Path(__file__).resolve().parents[4] / "frontend/apps/workbench/assets/styles/style.css").read_text()
JS = (Path(__file__).resolve().parents[4] / "frontend/apps/workbench/assets/scripts/app.js").read_text()


def escape(value):
    return html.escape(str(value))


def page(title, content, public_showcase=None):
    if public_showcase is None:
        public_showcase = os.getenv("RELAY_PUBLIC_SHOWCASE") == "1"
    environment = ("Vercel · Guided sandbox" if os.getenv("RELAY_PUBLIC_DEMO") == "1" else "Vercel · Read-only showcase") if public_showcase else "Local · Synthetic data"
    showcase = "<a href='/showcase'>Recorded demo</a>" if public_showcase else ""
    return HTMLResponse("<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
                        "<title>" + escape(title) + " · RelayOps</title><link rel='stylesheet' href='/assets/style.css'>"
                        "<aside><strong>RelayOps</strong><div class='muted'>Enterprise workflow lab</div><nav><a href='/uploads'>Use your own data</a><a href='/'>Overview</a><a href='/cases'>Cases</a><a href='/runs'>Investigations</a><a href='/architecture'>AI architecture</a>" + showcase + "</nav></aside>"
                        "<main><div class='top'><span>WORKSPACE / " + escape(title.upper()) + "</span><span class='pill'>" + environment + "</span></div>" + content +
                        "<div class='footer'>Evidence-backed proposals · Explicit sandbox review · No production connectors" + (" · Public actions disabled" if public_showcase else "") + "</div></main><script src='/assets/app.js' defer></script></html>")


class NewRun(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    case_id: Literal["short-shipment", "unknown-delivery", "low-stock", "healthy-delivery"]
    mode: Literal["scripted", "live"] = "scripted"
    browser: bool = True


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: str
    action: Literal["approve", "reject"]


class Execution(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: str


def create_app(state_dir):
    public_showcase = os.getenv("RELAY_PUBLIC_SHOWCASE") == "1"
    public_demo = public_showcase and os.getenv("RELAY_PUBLIC_DEMO") == "1"
    def render(title, content):
        return page(title, content, public_showcase)
    root = Path(state_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    store = RunStore(root)
    db = store.connection
    access_token = os.getenv("RELAY_ACCESS_TOKEN", "")
    public_origin = os.getenv("RELAY_PUBLIC_ORIGIN", "")
    if access_token and len(access_token) < 32:
        store.close()
        raise ValueError("RELAY_ACCESS_TOKEN must contain at least 32 characters")
    if public_origin and (urlsplit(public_origin).scheme != "https" or not access_token):
        store.close()
        raise ValueError("A public origin requires HTTPS and a private access token")
    embedded_worker = os.getenv("RELAY_EMBEDDED_WORKER", "0" if store.pool else "1") == "1"
    tasks = set()
    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            store.close()
    app = FastAPI(title="RelayOps public showcase" if public_showcase else "RelayOps local research workbench", lifespan=lifespan)
    app.state.store = store
    @app.middleware("http")
    async def boundaries(request, call_next):
        if public_showcase:
            from relayops.api.public_demo import WRITE_PATHS
            from relayops.uploads.api import WRITE_PATHS as UPLOAD_PATHS
            from relayops.product.api import WRITE_PATHS as ACCOUNT_PATHS
            UPLOAD_PATHS = UPLOAD_PATHS | ACCOUNT_PATHS
            if request.method != "GET" and not (public_demo and request.method == "POST" and request.url.path in (WRITE_PATHS | UPLOAD_PATHS)):
                return Response('{"detail":"Public showcase is read-only"}', status_code=405, media_type="application/json")
        else:
            host = request.headers.get("host", "").split(":")[0]
            allowed_hosts = {"127.0.0.1", "localhost", "testserver", urlsplit(public_origin).hostname}
            if host not in allowed_hosts:
                return Response("Unexpected host", status_code=403)
            probe = request.url.path in ("/healthz", "/readyz")
            if access_token and not probe:
                authorization = request.headers.get("authorization", "")
                expected = "Bearer " + access_token
                authenticated = secrets.compare_digest(authorization, expected)
                if authorization.startswith("Basic "):
                    try:
                        username, password = base64.b64decode(authorization[6:], validate=True).decode().split(":", 1)
                        authenticated = username == "operator" and secrets.compare_digest(password, access_token)
                    except (ValueError, UnicodeError):
                        authenticated = False
                if not authenticated:
                    return Response("Operator authentication required", status_code=401,
                                    headers={"WWW-Authenticate": 'Basic realm="RelayOps"'})
            elif not access_token and not probe and request.client and request.client.host not in ("127.0.0.1", "::1", "testclient"):
                return Response("Local workbench access only", status_code=403)
        if request.method != "GET":
            origin = request.headers.get("origin")
            if origin and origin not in ("http://" + request.headers["host"], "https://" + request.headers["host"]):
                return Response("Unexpected origin", status_code=403)
            if request.headers.get("content-type", "").split(";")[0] != "application/json" or len(await request.body()) > (1000000 if request.url.path.startswith(("/api/uploads/", "/api/account/")) else 16000):
                return Response("Bounded JSON body required", status_code=400)
        response = await call_next(request)
        image_sources = "'self' https://raw.githubusercontent.com" if public_showcase else "'self'"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src " + image_sources + "; frame-ancestors 'none'; base-uri 'none'"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
    def get_run(identity):
        if not re.fullmatch(r"[a-f0-9]{32}", identity):
            raise HTTPException(404, "Run unavailable")
        with db() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id=?", (identity,)).fetchone()
        if not row:
            raise HTTPException(404, "Run unavailable")
        return dict(row)
    def world_for(identity):
        return World(root / "runs" / identity / "world.sqlite")
    def report_for(identity):
        path = root / "runs" / identity / "assessment.json"
        return json.loads(path.read_text()) if get_run(identity)["status"] == "completed" and path.exists() else None
    def live_ready():
        profile=json.loads((Path(__file__).resolve().parents[4] / 'backend/data/pricing.json').read_text())
        return bool(os.getenv("ANTHROPIC_API_KEY") and os.getenv("RELAY_ALLOW_LIVE") == "1" and os.getenv("RELAY_MODEL") == profile['model'])
    @app.get("/healthz")
    def health():
        return {"status": "ok"}

    @app.get("/readyz")
    def readiness():
        try:
            with db() as connection:
                connection.execute("SELECT 1").fetchone()
        except Exception:
            return Response('{"status":"unavailable"}', status_code=503, media_type="application/json")
        return {"status": "ready"}

    @app.get("/assets/style.css")
    def stylesheet():
        return Response(CSS, media_type="text/css")
    @app.get("/assets/app.js")
    def javascript():
        return Response(JS, media_type="application/javascript")
    def cards():
        return "<div class='grid'>" + "".join("<a class='card' href='/cases/" + name + "'><div class='eyebrow'>Workflow case</div><h2>" + escape(value[0]) + "</h2><p class='muted'>" + escape(value[1]) + "</p><span>Inspect evidence →</span></a>" for name, value in SCENARIOS.items()) + "</div>"
    @app.get("/")
    def home():
        if public_demo:
            return FileResponse(Path(__file__).resolve().parents[4]/"frontend/apps/product/index.html", headers={"Cache-Control": "no-store"})
        with db() as connection:
            count = connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        release = "<div class='callout'><strong>Public engineering showcase.</strong> Explore the original cases and architecture, then open the recorded executed workflow. State-changing runs are disabled on the serverless deployment.</div>" if public_showcase else ""
        middle_label = "Executed walkthrough" if public_showcase else "Stored investigations"
        middle_value = "1" if public_showcase else str(count)
        provider = "Recorded evidence" if public_showcase else ("Configured" if live_ready() else "Not configured")
        return render("Overview", "<div class='hero'><div class='eyebrow'>Agentic operations / evidence to execution</div><h1>Resolve exceptions.<br>Verify every change.</h1><p class='muted'>Inspect applications and documents. Ground a plan in evidence. Review the exact proposed actions.</p></div>" + release + "<div class='stats'><div class='card'><div class='muted'>Workflow cases</div><div class='value'>4</div></div><div class='card'><div class='muted'>" + middle_label + "</div><div class='value'>" + middle_value + "</div></div><div class='card'><div class='muted'>AI evidence</div><div class='value'>" + provider + "</div></div></div>" + cards())
    @app.get("/cases")
    def cases():
        return render("Cases", "<div class='hero'><h1>Operational cases</h1><p class='muted'>Original synthetic workflows with independently checked outcomes.</p></div>" + cards())
    @app.get("/cases/{case_id}")
    def case(case_id):
        if case_id not in SCENARIOS:
            raise HTTPException(404, "Case unavailable")
        title, description, kwargs = SCENARIOS[case_id]
        state = fixture(name=case_id, **kwargs)
        source = "".join("<div class='card'><h3>" + escape(name.replace("_", " ").title()) + "</h3><pre>" + escape(json.dumps(state[name], indent=2)) + "</pre></div>" for name in ("procurement", "warehouse", "billing", "case_management"))
        disabled = "" if live_ready() else " disabled"
        action = ("<div class='card'><h2>Inspect the executed workflow</h2><p class='muted'>The public Vercel deployment is intentionally read-only. The recorded journey was produced by the actual isolated application and independently checked sandbox flow.</p><a class='button' href='/showcase'>Open recorded investigation</a><div class='callout'>No live model call or business effect is triggered by this public page.</div></div>" if public_showcase else "<div class='card'><h2>Start an investigation</h2><p class='muted'>The agent inspects four systems and two documents, records hypotheses and submits a grounded proposal.</p><label for='mode'>Execution mode</label><select id='mode'><option value='scripted'>Scripted integration · no model calls</option><option value='live'" + disabled + ">Live model-directed agent</option></select><button data-start='" + case_id + "'>Investigate with browser evidence</button><p id='error' class='error'></p><div class='callout'>Investigations produce proposals. Original sandbox business state changes only after explicit review and execution.</div></div>")
        return render(title, "<div class='hero'><a href='/cases'>← Cases</a><h1>" + escape(title) + "</h1><p class='muted'>" + escape(description) + "</p></div><div class='grid'><section>" + source + "</section><section>" + action + "<div class='card'><h2>Source documents</h2><pre>" + escape(json.dumps(state['documents'], indent=2)) + "</pre><p class='muted'>Browser-rendered original fixtures; real document extraction remains future work.</p></div></section></div>")
    @app.post("/api/runs")
    async def start_run(spec: NewRun, request: Request):
        key = request.headers.get("idempotency-key", "")
        if not key or len(key) > 100:
            raise HTTPException(400, "Bounded idempotency key required")
        if spec.mode == "live" and not live_ready():
            raise HTTPException(503, "Live agent is not privately configured")
        try:
            identity, status, created = await asyncio.to_thread(store.enqueue, spec.model_dump(), key)
        except Refused as error:
            raise HTTPException(409, str(error)) from None
        if created and embedded_worker:
            task = asyncio.create_task(run_one(store, identity))
            tasks.add(task)
            task.add_done_callback(tasks.discard)
        return {"id": identity, "status": status}
    @app.get("/api/runs/{identity}")
    def status(identity):
        row = get_run(identity)
        return {"id": identity, "case_id": row['case_id'], "mode": row['mode'], "status": row['status'], "review": row['review'],
                "events": len(world_for(identity).events()) if (root / "runs" / identity / "world.sqlite").exists() else 0,
                "error_kind": row.get("error_kind"), "assessment": report_for(identity)}
    @app.get("/runs")
    def runs():
        if public_showcase:
            return render("Investigations", "<div class='hero'><h1>Executed investigation</h1><p class='muted'>A recorded, source-bound walkthrough from the actual isolated application.</p></div><a class='card' href='/showcase'><div class='eyebrow'>Recorded evidence</div><h2>Short shipment · verified action</h2><p class='muted'>Five agent rounds · six evidence calls · one public correction · independent simulation · exact-version sandbox review.</p><span>Open walkthrough →</span></a>")
        with db() as connection:
            rows = list(connection.execute("SELECT id,case_id,mode,status FROM runs ORDER BY created_at DESC LIMIT 50"))
        content = "".join("<a class='row' href='/runs/" + row['id'] + "'><span>" + escape(row['case_id']) + "<br><small class='muted'>" + escape(row['mode']) + " · " + row['id'][:8] + "</small></span><span class='pill'>" + escape(row['status']) + "</span></a>" for row in rows)
        return render("Investigations", "<div class='hero'><h1>Investigations</h1><p class='muted'>Real stored records, evidence and execution receipts.</p></div><div class='card'>" + (content or "No investigations yet. Open a case to begin.") + "</div>")

    @app.get("/showcase")
    def showcase():
        if not public_showcase:
            raise HTTPException(404, "Showcase is available on the public deployment")
        return render("Recorded demo", "<div class='hero'><a href='/runs'>← Investigations</a><div class='eyebrow'>ACTUAL ISOLATED APP EXECUTION</div><h1>From cross-system evidence<br>to verified sandbox action.</h1><p class='muted'>Original synthetic short-shipment case with scripted model choices. No live inference or production financial effect.</p></div><div class='card'><img class='screen' src='https://raw.githubusercontent.com/Akhilesh-Vangala/relayops/main/docs/assets/relayops-demo.gif' alt='Recorded RelayOps investigation from evidence collection through verified sandbox effects'><p class='muted'>Five captured stages · 14 seconds · exact grayscale browser frames.</p></div><div class='stats'><div class='card'><div class='muted'>Agent rounds</div><div class='value'>5</div></div><div class='card'><div class='muted'>Evidence calls</div><div class='value'>6</div></div><div class='card'><div class='muted'>Public corrections</div><div class='value'>1</div></div></div><div class='grid'><div class='card'><h2>Authority boundary</h2><p>Read-only agent observation and proposal are separate from private-copy simulation, exact-version review and the action broker.</p></div><div class='card'><h2>Verified outcome</h2><p>$500 invoice hold, 20-unit claim and replacement reservation are checked in the isolated sandbox. Repeated execution reuses receipts without duplicate business effects.</p></div></div><div class='callout'>Engineering demonstration only. Live model quality, production connectors, individual identity and cloud worker execution remain release gates.</div>")
    @app.get("/runs/{identity}")
    def detail(identity):
        row, world = get_run(identity), world_for(identity)
        report = report_for(identity)
        events = world.events()
        activities = [e['payload'] for e in events if e['kind'] == 'agent_activity']
        timeline = "".join("<div class='step'><strong>" + escape(event['stage'].replace('_', ' ')) + "</strong><br><small>Round " + escape(event.get('round', 0)) + (" · " + escape(event['status']) if event.get('status') else "") + "</small></div>" for event in activities)
        head = "<div class='hero' data-run-id='" + identity + "' data-status='" + row['status'] + "' data-events='" + str(len(events)) + "'><a href='/runs'>← Investigations</a><h1>" + escape(SCENARIOS[row['case_id']][0]) + "</h1><span class='pill'>" + escape(row['status']) + "</span> <span class='muted'>" + escape(row['mode']) + " · " + identity[:8] + "</span></div>"
        evidence = ""
        proposed = "<div class='card'><h2>Agent assessment</h2><p class='muted'>Evidence and proposals appear as actual execution completes.</p></div>"
        if report:
            plan, version = report['plan'], report['version']
            hypotheses = "".join("<div class='row'><span>" + escape(h['claim']) + "</span><span class='pill'>" + escape(h['assessment']) + "</span></div>" for h in report['hypotheses'])
            labels={'hold_invoice':'Hold disputed invoice amount','open_supplier_claim':'Open shortage claim','reserve_replacement':'Reserve replacement stock','resolve_case':'Resolve case'}
            def action_value(action):
                if action['kind']=='hold_invoice':
                    return f"${action['amount']//100:,}.{action['amount']%100:02d}"
                return str(action['amount'])+' units' if action['kind']!='resolve_case' else 'Resolved'
            actions = "".join("<tr><td>" + labels[a['kind']] + "</td><td>" + escape(action_value(a)) + "</td></tr>" for a in plan['actions'])
            checks = "".join("<div class='row'><span>" + escape(name.replace('_',' ')) + "</span><span>" + ('Passed' if passed else 'Failed') + "</span></div>" for name,passed in report['simulation']['checks'].items())
            controls = "<p class='muted'>This result proposes no business writes.</p>"
            if plan['actions']:
                if row['review'] == 'approved':
                    controls = "<p>Exact proposal approved in local sandbox.</p><button data-execute='" + identity + "' data-version='" + version + "'>Execute approved sandbox actions</button>"
                elif row['review'] == 'rejected':
                    controls = "<p>Proposal rejected. Execution blocked.</p>"
                else:
                    controls = "<div class='toolbar'><button data-review='approve' data-run='" + identity + "' data-version='" + version + "'>Approve sandbox proposal</button><button class='secondary' data-review='reject' data-run='" + identity + "' data-version='" + version + "'>Reject</button></div>"
            proposed = "<div class='stats'><div class='card'><div class='muted'>Model rounds</div><div class='value'>" + str(report['rounds']) + "</div></div><div class='card'><div class='muted'>Evidence calls</div><div class='value'>" + str(report['tool_calls']) + "</div></div><div class='card'><div class='muted'>Corrections</div><div class='value'>" + str(report['corrections']) + "</div></div></div><div class='card'><h2>Public hypothesis memory</h2>" + hypotheses + "</div><div class='card'><h2>Proposed business actions</h2><span class='pill'>" + escape(plan['outcome']) + "</span><p>" + escape(plan['explanation']) + "</p><table><tr><th>Action</th><th>Proposed change</th></tr>" + actions + "</table></div><div class='card'><h2>Counterfactual verification</h2>" + checks + "</div><div class='card'><h2>Exact-version review</h2><p class='muted'>This controls synthetic sandbox effects only.</p>" + controls + "<p id='error' class='error'></p></div>"
            evidence = "<div class='card'><h2>Observed sources and screenshots</h2>" + "".join("<details><summary>" + escape(record['system']) + " · " + record['evidence_id'][:10] + "</summary><pre>" + escape(json.dumps(record['data'], indent=2)) + "</pre>" + ("<img class='screen' src='/api/runs/" + identity + "/observations/" + record['evidence_id'] + ".png' alt='Actual captured synthetic evidence page'>" if record.get('browser') else "") + "</details>" for record in report['evidence']) + "</div>"
            if row['execution']:
                verified=json.loads(row['execution'])
                actual_checks=''.join("<div class='row'><span>"+escape(name.replace('_',' '))+"</span><span>"+('Passed' if passed else 'Failed')+"</span></div>" for name,passed in verified['checks'].items())
                proposed += "<div class='card'><h2>Execution verification</h2>"+actual_checks+"<details><summary>Inspect audit report</summary><pre>" + escape(json.dumps(verified, indent=2)) + "</pre></details></div>"
        return render("Investigation", head + "<div class='grid'><section>" + proposed + evidence + "</section><section><div class='card'><h2>Actual agent activity</h2><div class='timeline'>" + (timeline or "Awaiting worker activity.") + "</div></div><div class='card'><h2>Execution boundaries</h2><p class='muted'>Read-only investigation. Cited public memory. Independent simulation. Explicit sandbox approval. Durable action receipts.</p><p class='muted'>Live quality and cloud operation remain unverified.</p></div></section></div>")
    @app.get("/api/runs/{identity}/observations/{image_name}")
    def screenshot(identity, image_name):
        get_run(identity)
        if not re.fullmatch(r"[a-f0-9]{64}\.png", image_name):
            raise HTTPException(404, "Observation unavailable")
        report = report_for(identity)
        record = next((r for r in (report or {}).get('evidence', []) if r['evidence_id'] + '.png' == image_name and r.get('browser')), None)
        path = root / "runs" / identity / "observations" / image_name
        if not record or not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != record['browser']['png_sha256']:
            raise HTTPException(409, "Stored observation integrity check failed")
        return Response(path.read_bytes(), media_type="image/png")
    def checked_report(identity, version):
        row, report = get_run(identity), report_for(identity)
        if row['status'] != 'completed' or not report or report['version'] != version or not report['simulation']['passed']:
            raise HTTPException(409, "Exact completed verified assessment required")
        stored = dict(report); stored.pop('version')
        if digest(stored) != version:
            raise HTTPException(409, "Assessment integrity check failed")
        world = world_for(identity)
        pricing = json.loads((Path(__file__).resolve().parents[4] / "backend/data/pricing.json").read_text()) if row['mode'] == 'live' else None
        client = SimpleNamespace(mode=report['client_mode'], pricing=pricing)
        metadata = json.loads((world.path.parent / 'agent-version.json').read_text())
        if metadata['fingerprint'] != fingerprint(world, True if report['browser_observations'] else None, client):
            raise HTTPException(409, "Source/runtime changed; obtain a fresh assessment")
        return row, report
    @app.post("/api/runs/{identity}/review")
    def review(identity, value: Review):
        row, report = checked_report(identity, value.version)
        with db() as connection:
            connection.execute("BEGIN IMMEDIATE")
            fresh = connection.execute("SELECT review FROM runs WHERE id=?", (identity,)).fetchone()
            if fresh[0]:
                raise HTTPException(409, "Review is immutable")
            try:
                token = approve(world_for(identity), Plan.from_json(report['plan']), operator='local-sandbox-operator') if value.action == 'approve' else None
            except Refused as error:
                raise HTTPException(409, str(error)) from None
            connection.execute("UPDATE runs SET review=?,approval=? WHERE id=?", ('approved' if value.action=='approve' else 'rejected', token, identity))
        return {"review": value.action, "version": value.version}
    @app.post("/api/runs/{identity}/execute")
    def execute_run(identity, value: Execution):
        row, report = checked_report(identity, value.version)
        if row['review'] != 'approved' or not row['approval']:
            raise HTTPException(409, "Explicit approved sandbox proposal required")
        world = world_for(identity)
        original = fixture(name=row['case_id'], **SCENARIOS[row['case_id']][2])
        try:
            execute(world, Plan.from_json(report['plan']), row['approval'])
        except Refused as error:
            raise HTTPException(409, str(error)) from None
        result = evaluate(original, world.state(), world.events(), report['plan']['outcome'])
        with db() as connection:
            connection.execute("UPDATE runs SET execution=? WHERE id=?", (json.dumps(result), identity))
        return result
    @app.get("/architecture")
    def architecture():
        layers = [('Observe','Scoped system tools plus browser screenshots/accessibility and document observations.'),
                  ('Reason','Model-directed tool selection, cited public hypotheses and bounded correction.'),
                  ('Remember','Persistent graph checkpoints, runtime/source fingerprints and recent-image context policy.'),
                  ('Verify','Public plan policy, private counterfactual execution and independent final-state assertions.'),
                  ('Authorize','Exact-version review and controlled sandbox action identities.'),
                  ('Recover','Unknown receipts block retry; explicit reconciliation before continuation.')]
        return render('AI architecture',"<div class='hero'><h1>From evidence to verified actions</h1><p class='muted'>Implemented layers with explicit authority boundaries.</p></div><div class='grid'>"+''.join("<div class='card'><div class='eyebrow'>"+escape(title)+"</div><h2>"+escape(text)+"</h2></div>" for title,text in layers)+"</div><div class='callout'>Current: PostgreSQL coordination with separate leased browser workers and Docker/Kubernetes packaging. Fixture worlds and agent checkpoints remain local files. Individual identity, isolated customer execution, production connectors and monitored cloud deployment remain pending.</div>")
    if public_demo:
        from relayops.api.public_demo import attach
        attach(app, SCENARIOS)
    from relayops.uploads.api import attach as attach_uploads
    attach_uploads(app, "RelayOps", Path(__file__).resolve().parents[4])
    from relayops.product.api import attach as attach_product
    attach_product(app, Path(__file__).resolve().parents[4])
    return app


def main():
    import argparse
    import uvicorn
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8100)
    parser.add_argument('--state-dir',type=Path,default=Path('artifacts/generated/app'))
    args = parser.parse_args()
    uvicorn.run(create_app(args.state_dir),host='127.0.0.1',port=args.port)


if __name__ == '__main__':
    main()
