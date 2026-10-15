"""Vercel entrypoint for the interactive synthetic RelayOps sandbox."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend" / "src"))

os.environ["RELAY_ALLOW_LIVE"] = "0"
os.environ["RELAY_PUBLIC_SHOWCASE"] = "1"
os.environ["RELAY_PUBLIC_DEMO"] = "1"
os.environ["RELAY_EMBEDDED_WORKER"] = "0"
os.environ["RELAY_DATABASE_URL"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""

from relayops.api.web import create_app  # noqa: E402

app = create_app(Path("/tmp/relayops-public-showcase"))
