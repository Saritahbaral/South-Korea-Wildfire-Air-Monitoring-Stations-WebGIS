"""Open the research WebGIS from VS Code's Run button or a terminal."""
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
try:
    import streamlit  # noqa: F401
    import folium  # noqa: F401
    import streamlit_folium  # noqa: F401
except ImportError:
    raise SystemExit("Install the viewer packages first: python -m pip install -r requirements.txt")

raise SystemExit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(HERE / "app.py"),
                                  "--server.address", "127.0.0.1", "--browser.serverAddress", "127.0.0.1"],
                                 cwd=HERE))
