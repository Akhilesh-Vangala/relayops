"""Request-bounded own-data APIs and their standalone product workspace."""

import hmac
import os
import secrets
import time
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .ingestion import (
    Upload,
    Preview,
    UploadBoundary,
    UploadProblem,
    fingerprint,
    profile,
    preview,
)
from .service import run
from .signing import attest, verify_report
from .imports import FileImport, FORMATS, import_file

WRITE_PATHS = {
    "/api/uploads/import",
    "/api/uploads/profile",
    "/api/uploads/preview",
    "/api/uploads/analyze",
    "/api/uploads/analyze-stream",
    "/api/uploads/check-report",
    "/api/uploads/approve",
}


class ReportCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    report: dict[str, Any] = Field(max_length=32)


MAX_CASES = 30

CONFIGS = {
    "RelayOps": {
        "title": "Turn operational cases into reviewed updates.",
        "description": "Upload open short-shipment cases. Inspect evidence, policies and simulated outcomes before approving a downloadable change set.",
        "fields": [
            ["order_id", "Order / case ID", True],
            ["ordered", "Ordered units", True],
            ["received", "Received units", True],
            ["invoiced", "Invoiced units", True],
            ["available", "Available replacement units", True],
            ["unit_price", "Unit price", True],
            ["confirmed", "Delivery confirmed (true / false)", True],
            ["pool", "Shared inventory pool / SKU", False],
        ],
        "options": [["unit", "Price unit", ["dollars", "cents"]]],
        "template": "order_id,ordered_units,received_units,invoiced_units,available_units,unit_price,delivery_confirmed,inventory_pool\nPO-901,15,10,15,8,12.50,true,SKU-A\nPO-902,8,3,8,8,12.50,true,SKU-A\nPO-903,6,6,6,4,8.00,true,SKU-B\n",
        "suggest": {
            "order_id": ["order_id"],
            "ordered": ["ordered_units"],
            "received": ["received_units"],
            "invoiced": ["invoiced_units"],
            "available": ["available_units"],
            "unit_price": ["unit_price", "unit_cents"],
            "confirmed": ["delivery_confirmed"],
            "pool": ["inventory_pool", "sku"],
        },
        "notice": "Upload only open cases with no existing holds, claims or reservations. A mapped pool shares its initial stock across rows; without a pool, stock is allocated separately to each order. Approval exports proposed changes; it never writes to an ERP or supplier system.",
    },
}


def attach(app, project, root):
    config = CONFIGS[project]
    static = Path(root) / "frontend/apps/uploads"
    app.add_middleware(UploadBoundary)
    from relayops.api.demo_security import DemoSession

    secret = os.getenv("RELAY_DEMO_SECRET", "")
    if not secret and os.getenv("RELAY_PUBLIC_SHOWCASE") != "1":
        secret = secrets.token_urlsafe(64)
    session = DemoSession(secret, "relay_upload_visitor") if secret else None

    @app.get("/uploads", include_in_schema=False)
    def workspace():
        return FileResponse(
            Path(root) / "frontend/apps/product/index.html",
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            },
        )

    @app.get("/uploads/recording.html", include_in_schema=False)
    def recording():
        return FileResponse(
            static / "recording.html", headers={"Cache-Control": "no-store"}
        )

    @app.get("/uploads-assets/{name}", include_in_schema=False)
    def assets(name: str):
        if name not in (
            "style.css",
            "recording.html",
            "walkthrough.webm",
            "poster.png",
        ):
            raise HTTPException(404, "Asset unavailable")
        return FileResponse(static / name, headers={"Cache-Control": "no-store"})

    @app.get("/api/uploads/capabilities")
    def capabilities(request: Request, response: Response):
        if session:
            session.visitor(request, response)
        response.headers["Cache-Control"] = "no-store"
        return {
            "project": project,
            **{k: v for k, v in config.items() if k != "template"},
            "live_ai": False,
            "run_record_schema": "run-v1",
            "formats": sorted(FORMATS),
            "max_csv_bytes": 400000,
            "max_rows": MAX_CASES,
            "retention": "Unsaved files are processed for this request and remain in browser memory. Optional device history or configured account storage requires explicit save consent. Hosting metadata may be retained; file contents are not deliberately logged.",
            "approval_available": session is not None,
        }

    @app.get("/api/uploads/template")
    def template():
        return Response(
            config["template"],
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{project.lower()}-template.csv"',
                "Cache-Control": "no-store",
            },
        )

    @app.post("/api/uploads/import")
    def import_tabular(body: FileImport):
        try:
            return JSONResponse(
                import_file(body, max_rows=MAX_CASES),
                headers={"Cache-Control": "no-store"},
            )
        except UploadProblem as error:
            return JSONResponse(error.response(), status_code=422)
        except ValueError:
            raise HTTPException(
                422, "Invalid tabular file; check the export and retry"
            ) from None

    @app.post("/api/uploads/profile")
    def inspect(upload: Upload):
        try:
            inspected = profile(upload.csv)
            if inspected["rows"] > MAX_CASES:
                raise ValueError(
                    f"Operational assessment supports at most {MAX_CASES} open cases per export"
                )
            return inspected
        except UploadProblem as error:
            return JSONResponse(error.response(), status_code=422)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.post("/api/uploads/analyze")
    def analyze(upload: Upload, request: Request):
        try:
            result = run(upload)
        except UploadProblem as error:
            return JSONResponse(error.response(), status_code=422)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        if session:
            result["review"] = session.seal(
                {
                    "visitor": session.visitor(request),
                    "source": fingerprint(
                        {
                            "csv": upload.csv,
                            "mapping": upload.mapping,
                            "options": upload.options,
                        }
                    ),
                    "plan": result["plan_sha256"],
                    "expires": int(time.time()) + 900,
                },
                "upload-review-v1",
            )
        return JSONResponse(
            attest(result),
            headers={
                "Cache-Control": "no-store",
                "X-Run-ID": result["run_record"]["run_id"],
            },
        )

    @app.post("/api/uploads/preview")
    def preview_rows(body: Preview):
        try:
            return preview(body)
        except UploadProblem as error:
            return JSONResponse(error.response(), status_code=422)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.post("/api/uploads/analyze-stream")
    def analyze_stream(upload: Upload, request: Request):
        from .stream import stream

        def finish(result):
            if session:
                result["review"] = session.seal(
                    {
                        "visitor": visitor,
                        "source": fingerprint(
                            {
                                "csv": upload.csv,
                                "mapping": upload.mapping,
                                "options": upload.options,
                            }
                        ),
                        "plan": result["plan_sha256"],
                        "expires": int(time.time()) + 900,
                    },
                    "upload-review-v1",
                )
            return attest(result)

        visitor = session.visitor(request) if session else None
        return stream(upload, finish)

    @app.post("/api/uploads/check-report")
    def check_saved_report(body: ReportCheck):
        return {
            "verified": verify_report(body.report),
            "scope": "Authenticity of a past computed report; not a fresh source-system check.",
        }

    @app.post("/api/uploads/approve")
    def approve_export(upload: Upload, request: Request):
        if not session:
            raise HTTPException(503, "Approval signing is not configured")
        state = session.open(upload.review, "upload-review-v1")
        if not hmac.compare_digest(state.get("visitor", ""), session.visitor(request)):
            raise HTTPException(403, "Review belongs to a different browser")
        source = fingerprint(
            {"csv": upload.csv, "mapping": upload.mapping, "options": upload.options}
        )
        if not hmac.compare_digest(state.get("source", ""), source):
            raise HTTPException(
                409, "File or contract changed after review; analyze again"
            )
        try:
            preview = run(upload)
            if not hmac.compare_digest(state.get("plan", ""), preview["plan_sha256"]):
                raise HTTPException(409, "Plan changed after review; analyze again")
            result = run(upload, approved=True)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        return JSONResponse(
            attest(result),
            headers={
                "Cache-Control": "no-store",
                "X-Run-ID": result["run_record"]["run_id"],
            },
        )
