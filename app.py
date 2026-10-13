"""Vercel entrypoint for the public, read-only RelayOps engineering showcase."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

os.environ["RELAY_ALLOW_LIVE"] = "0"
os.environ["RELAY_PUBLIC_SHOWCASE"] = "1"

from relayops.web import create_app  # noqa: E402

app = create_app(Path("/tmp/relayops-public-showcase"))
