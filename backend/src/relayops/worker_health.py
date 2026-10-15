"""Container liveness for the polling worker and its active lease renewal."""
import os
import time
from pathlib import Path


def main():
    path = Path(os.getenv("RELAY_WORKER_HEARTBEAT", "/tmp/relayops-worker-heartbeat"))
    try:
        if time.time() - path.stat().st_mtime > 30:
            raise ValueError("stale heartbeat")
        os.kill(int(path.read_text()), 0)
    except (OSError, ValueError):
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
