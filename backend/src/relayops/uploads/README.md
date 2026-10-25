# uploads

Bounded imports, per-case assessment, streaming progress and signed reports. Uploaded data is never written to shared history.

- `imports.py`: CSV, TSV, XLSX, JSON and JSONL normalization with workbook safety checks
- `ingestion.py`: body, file, row, column and cell bounds, profiling and preview
- `service.py`: per-case LangGraph assessment, shared-stock allocation, approval and execution
- `stream.py`: SSE mailbox with a terminal slot and a 25-second deadline
- `signing.py`: report HMAC
- `api.py`: `/api/uploads/*` endpoints

[Data imports](../../../../docs/product/DATA-IMPORTS.md)
