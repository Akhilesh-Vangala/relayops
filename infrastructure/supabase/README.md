# Supabase

[001_product_workspace.sql](migrations/001_product_workspace.sql) creates owner-isolated, immutable project and investigation tables with forced row-level security, owner-scoped foreign keys and serialized per-owner quotas. The application needs only the HTTPS project URL and a publishable key. It refuses service and admin keys.

```sh
RELAY_PRODUCT_TEST_ADMIN_URL=postgresql://… python scripts/checks/product_rls.py
```

The check creates and drops its own disposable database.

[Product workspace](../../docs/product/WORKSPACE.md#optional-cloud-accounts)
