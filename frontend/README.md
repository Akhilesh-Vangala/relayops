# Frontend

Native browser applications served by FastAPI. There is no build step and no Node service.

| App | Path | Served at |
| --- | --- | --- |
| [Product workspace](apps/product/) | ES modules, IndexedDB storage, SSE | `/`, `/workspace/*`, `/uploads` |
| [Interactive sandbox](apps/demo/) | Single-page app over `/api/demo/*` | `/demo/*` |
| [Operator workbench](apps/workbench/) | Assets for server-rendered pages | Local and durable runtime |
| [Upload walkthrough](apps/uploads/) | Recording page and media | `/uploads/recording.html` |

[Layout](../docs/development/LAYOUT.md)
