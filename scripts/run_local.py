"""
Sri Lanka FloodWatch — Local Development & Competition Demo Launcher Script.

Boots the FastAPI application on http://127.0.0.1:8000/ and opens the local website.
"""

import sys
import os
import webbrowser
import time
from pathlib import Path

# Add project root directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


def main():
    print("=" * 70)
    print("  SRI LANKA FLOODWATCH — LOCAL COMPETITION DEMO LAUNCHER")
    print("=" * 70)
    print("Starting local FastAPI application server on http://127.0.0.1:8000/...")
    print("Press Ctrl+C to stop the local server.\n")

    # Open local website in default browser after 1.5 seconds delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8000/")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # Launch Uvicorn server
    import uvicorn
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
