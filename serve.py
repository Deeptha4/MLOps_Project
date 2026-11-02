"""Entry point: start the Prometheus endpoint immediately, then run Streamlit in-process.

Starting the metrics server here (not inside app.py) means /metrics is up as soon as the
container starts, so Prometheus sees the target as UP even before anyone opens the app.
"""

import os
import sys
from pathlib import Path

from prometheus_client import start_http_server
from streamlit.web import cli as stcli

if __name__ == "__main__":
    start_http_server(int(os.getenv("METRICS_PORT", "8000")))
    sys.argv = [
        "streamlit",
        "run",
        str(Path(__file__).parent / "app.py"),
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--server.headless=true",
    ]
    sys.exit(stcli.main())
