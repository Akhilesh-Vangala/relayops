"""Persistent container entrypoint; the public Vercel entrypoint stays separate."""
import os
from .web import create_app


def application():
    return create_app(os.getenv("RELAY_STATE_DIR", "/state"))
