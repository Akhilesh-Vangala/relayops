# Product workspace

Native ES modules and semantic HTML. `app.js` owns routing and controllers, `state.js` holds unsaved state, `lib/` owns DOM, HTTP, SSE and IndexedDB access, and `views/` renders the landing, intake, report and account pages. Source data is rendered as text nodes. Saving requires explicit consent.

```sh
python scripts/demos/product_browser.py --axe <path to axe.min.js>
```

[Product workspace](../../../docs/product/WORKSPACE.md)
