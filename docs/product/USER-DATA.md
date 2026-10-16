## Multiple tabular formats — October16

CSV, TSV, Excel .xlsx, JSON and JSONL are accepted through the guided product. [Formats, worksheet selection, exact conversion and limits](FILE-IMPORTS.md). Existing domain contracts and result/approval checks remain applicable; PDFs/images are unsupported. Earlier CSV-specific implementation descriptions below remain historical context for the normalized analysis engine.

# RelayOps: work with your own data

The public `/uploads` workspace accepts visitor-owned CSVs and returns source-derived results. Existing sample investigations remain separate. No provider keys are configured in the public deployment: these are explicitly reviewed contract workflows, not live language interpretation or measured general-purpose agent accuracy.

```mermaid
flowchart LR
    A[Visitor CSV] --> B[Bounded parse and profile]
    B --> C[Review column and business contract]
    C --> D[Execute source-derived workflow]
    D --> E[Independent verification]
    E --> F[Review results and export]
```

## Business contract

Map one row per previously unprocessed open order: order ID, ordered/received/invoiced quantities, available replacement stock, unit price and explicit delivery confirmation (`true` or `false`). An optional inventory-pool/SKU field makes stock shared. Each pool's initial stock must agree on every row. Without this field, availability is explicitly per-order allocated stock. Existing holds, reservations and claims must have been excluded before upload; this contract does not ingest existing effects.

Rows are processed in sorted order-ID order, allocating shared stock conservatively. Each source-derived temporary world runs the real `observe → propose → policy → simulate` LangGraph using `DiagnosticPlanner`. Its known business rule is deterministic; no model inference is claimed. Unknown delivery, inconsistent invoice quantities or insufficient remaining stock produce `needs_information`, never an automatic change. Overdelivery is outside the contract and refuses the export.

Review displays exact proposed actions and independently checked simulations. Approval uses an HttpOnly, SameSite Strict browser cookie and a separately purpose-bound HMAC envelope with a 15-minute expiry, source/contract hash and aggregate plan hash. The envelope contains no uploaded rows. A follow-up request resends the browser-held original, verifies the source and recomputed plans, then performs approval/execution against newly reconstructed temporary worlds. Only independently verified effects appear in the downloadable CSV and JSON receipts. Repeated approval regenerates an equivalent export; it is not a distributed exactly-once ERP transaction. No vendor, payment or inventory system is contacted.

## Data handling and limits

- UTF-8 comma-separated CSV with one header row; maximum 400,000 UTF-8 bytes, 60 columns, 120 characters per header and 2,048 characters per cell. Case-insensitive duplicate headers, ragged records, invalid control characters and empty files are refused.
- At most 30 rows per analysis; at most 100 aggregate result groups. Each numeric source value is at most 100 million in magnitude; RelayOps also enforces its existing ten-million action bound.
- The browser reads a selected file and transmits its CSV text inside bounded JSON. An outer ASGI middleware counts actual streamed bytes before JSON decoding, rejects bodies over 1 MB and limits body reception to 15 seconds. No multipart package is necessary.
- Parsing/analysis run in FastAPI's synchronous handler thread pool, outside the event loop. This does not provide global admission control across serverless instances.
- Processing uses memory and, for operational worlds, automatically cleaned temporary scratch. Original rows/results are not deliberately persisted in shared history, application logs, browser local storage or session storage by default. Explicit device save uses IndexedDB, and configured cloud save requires separate consent. Unsaved browser files/results disappear on reload or Clear. Explicit consent now enables immutable IndexedDB snapshots and portable backups; see [product storage](PRODUCT-WORKSPACE.md). Hosting providers may retain request metadata; this is not a confidential-data hosting certification.
- User content is rendered with text nodes, never HTML. CSV exports neutralize formula-like text while preserving typed numeric negatives. Filenames never become server filesystem paths. No uploaded code, external URLs, extensions or arbitrary SQL are executed.
- Live generation, tenant identity, persistent connector credentials, durable uploaded datasets, asynchronous large-file jobs and monitored customer execution are separate release gates.

The app's limits remain below [Vercel's request/response payload limit](https://vercel.com/docs/functions/limitations). Larger exports need a separately designed direct-object-upload and durable-worker flow, not a larger JSON request.

## Endpoints

`GET /api/uploads/capabilities`, `GET /api/uploads/template`, `POST /api/uploads/profile`, `POST /api/uploads/analyze`, `POST /api/uploads/preview`, `POST /api/uploads/analyze-stream`, `POST /api/uploads/check-report`, and `POST /api/uploads/approve` for the exact reviewed RelayOps export. The narrow public upload allowlist does not enable legacy state-changing operator endpoints. Every analysis request includes the original CSV and explicit mapping/options. API responses are not cached.

See the implementation's `uploads` package and `backend/tests/api/test_uploads.py` for independently authored expected values, changed-input, validation and isolation regressions. Local/deployed verification is recorded in the project handoff after it actually runs.
