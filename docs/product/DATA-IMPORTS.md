# Data imports

## Business contract

Each row is one open, previously unprocessed order. The required columns are the order ID, ordered, received and invoiced quantities, unit price, available replacement stock, and an explicit delivery confirmation (`true` or `false`). An optional inventory pool or SKU column makes stock shared, in which case every row in a pool must report the same initial stock. Rows must not already carry holds, claims or reservations.

Outcomes follow the [policy](../architecture/EXECUTION.md#policy-admission). Unknown delivery, an invoice that disagrees with the order, or stock that cannot cover the shortage yields `needs_information` and no changes. Over-delivery is outside the contract and blocks the export.

## Formats

| Format | Accepted shape |
| --- | --- |
| CSV | UTF-8 with one header row. The original text, including any BOM and CRLF line endings, is kept for source fingerprints. |
| TSV | UTF-8 tab-separated with one header row, using CSV quoting rules |
| XLSX | A rectangular table starting at row 1. Multi-sheet workbooks require choosing one visible sheet. Numeric cells use stored values, text IDs keep leading zeros, and dates become ISO text without an invented timezone. |
| JSON | A non-empty array of flat objects with identical keys. Numbers are parsed as `Decimal`. |
| JSONL | One flat object per line with identical keys. Blank lines are refused. |

Every format is normalized to an inspectable CSV table. The browser records the format, the chosen sheet, the SHA-256 of the original file and the SHA-256 of the normalized table. PDFs, images, `.xls`, `.xlsm`, archives and Parquet are refused.

## Limits

| Limit | Value |
| --- | --- |
| Request body | 1 MB, counted from the streamed bytes before JSON decoding, with a 15 s receive deadline |
| Source file or normalized table | 400,000 bytes |
| Columns | 60, headers up to 120 characters |
| Cell | 2,048 characters |
| Parsed rows | 5,000 |
| Cases per operational export | 30 |
| Numeric magnitude | 100,000,000, plus the 10,000,000 action bound |

## Workbook safety

XLSX files load through pinned `openpyxl` in read-only mode with `defusedxml`. Before loading, the ZIP container is checked: at most 200 members, 8 MB total expansion, 4 MB per member, a compression ratio of at most 150:1, and no duplicate, path-traversing or encrypted entries. DTDs and entities, formulas, merged cells, macros, external links, embedded objects and ActiveX controls are refused. Declared dimensions are not trusted, because actual rows and cells are bounded independently.

## Output safety

Errors return structured guidance that names the record and column, without raw cell values or parser traces. CSV exports neutralize formula-like text and preserve typed negative numbers. Filenames never become filesystem paths. No uploaded code, URLs or SQL are executed.

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/uploads/capabilities` | Formats and limits |
| `GET /api/uploads/template` | Example source |
| `POST /api/uploads/import` | `filename`, `content_base64` and optional `sheet`. Returns the normalized table and profile, or `needs_sheet`. |
| `POST /api/uploads/profile`, `/preview` | Column quality and selected-record preview |
| `POST /api/uploads/analyze`, `/analyze-stream` | Assessment, streamed over SSE |
| `POST /api/uploads/check-report` | Server authentication of a saved report |
| `POST /api/uploads/approve` | Exact-snapshot approval and checked export |

In the public build, writes are accepted only on these routes, the `/api/demo/*` routes and the `/api/account/*` routes. Every other write endpoint returns HTTP 405.

[Product workspace](WORKSPACE.md)
