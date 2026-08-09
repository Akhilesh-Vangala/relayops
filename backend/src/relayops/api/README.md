# api

FastAPI application, security middleware and the public sandbox.

- [web.py](web.py): app factory, operator workbench routes, origin and body checks, security headers
- [public_demo.py](public_demo.py): request-scoped `/api/demo/*` investigate, review, execute and reconcile
- [demo_security.py](demo_security.py): HMAC envelopes bound to an HttpOnly visitor cookie
- [asgi.py](asgi.py): ASGI entrypoint for containers

[Deployment](../../../../docs/operations/DEPLOYMENT.md)
