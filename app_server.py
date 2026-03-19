"""
app_server.py  -  Unified entry-point for the packaged DUBGG EXE.

Serves the FastAPI backend AND the compiled React frontend from a single
process so the EXE is entirely self-contained.

Fixes applied:
  - Catch-all route now checks for real files first (fixes white-screen /
    broken JS/CSS assets issue when the SPA catch-all was swallowing them).
  - Binds to 127.0.0.1 by default to avoid the Windows Firewall pop-up on
    restricted machines. Pass --host 0.0.0.0 on the command line if you
    need LAN access.
"""

import os
import sys
import threading
import time
import webbrowser
import logging
import argparse

# ---------------------------------------------------------------------------
# Resolve bundled-file locations
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    _BASE_DIR = sys._MEIPASS          # PyInstaller temp extraction folder
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_DIR = os.path.join(_BASE_DIR, "frontend_dist")

# Make utils/ importable in both frozen and unfrozen modes
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

# ---------------------------------------------------------------------------
# Bring in the FastAPI app from api_server (do NOT re-run uvicorn from there)
# ---------------------------------------------------------------------------
from api_server import app  # noqa: E402

from fastapi import Request, APIRouter
from fastapi.responses import FileResponse, HTMLResponse
import mimetypes

# Fix for Windows registry sometimes missing the JS content type
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SPA catch-all route
#
# KEY FIX:  We check whether the requested path maps to a real file inside
# frontend_dist/ first.  If it does (e.g. /assets/index-abc123.js) we serve
# it directly.  Only if the file does NOT exist do we return index.html so
# React Router can handle client-side navigation.
#
# Without this check the old catch-all was returning index.html for every
# /assets/* request, which the browser rejected as "not valid JS/CSS",
# resulting in a white screen even though the title loaded.
# ---------------------------------------------------------------------------

if os.path.isdir(STATIC_DIR):
    logger.info("Serving React frontend from: %s", STATIC_DIR)
else:
    logger.warning(
        "Frontend build not found at %s. "
        "Run 'npm run build' and rebuild the EXE.",
        STATIC_DIR,
    )


# ---------------------------------------------------------------------------
# SPA Catch-all (Logic moved to __main__ block for priority)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Auto-open browser after a short delay
# ---------------------------------------------------------------------------
def _open_browser(host: str, port: int):
    time.sleep(2.5)
    url = f"http://{'localhost' if host == '0.0.0.0' else host}:{port}"
    webbrowser.open(url)


# ---------------------------------------------------------------------------
# SPA Catch-all
# ---------------------------------------------------------------------------
def setup_spa(app_instance):
    spa_router = APIRouter()
    
    @spa_router.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(request: Request, full_path: str):
        # Guard against directory traversal
        safe_path = os.path.normpath(full_path).lstrip(os.sep).lstrip("/")
        candidate = os.path.join(STATIC_DIR, safe_path)

        if os.path.isfile(candidate) and not safe_path == "":
            return FileResponse(candidate)

        # SPA fallback
        index_html = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index_html):
            response = FileResponse(index_html)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response

        return HTMLResponse("Frontend not found", status_code=404)
    
    # Mount SPA router AFTER all other routes are already in app_instance
    app_instance.include_router(spa_router)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    # Mount SPA routes explicitly AFTER API routes
    setup_spa(app)

    parser = argparse.ArgumentParser(description="DUBGG Generator HMI Server")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help=(
            "Host to bind to. "
            "Default: 127.0.0.1 (localhost only, no firewall prompt). "
            "Use 0.0.0.0 for LAN access (requires admin firewall approval)."
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8500,
        help="Port to listen on (default: 8500).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open the browser on startup.",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("  DUBGG Generator HMI")
    logger.info("  http://%s:%d", args.host, args.port)
    logger.info("=" * 60)

    if not args.no_browser:
        threading.Thread(
            target=_open_browser, args=(args.host, args.port), daemon=True
        ).start()

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        access_log=False,
        reload=False,
    )
