"""
Vercel Serverless Function Entrypoint for Sri Lanka FloodWatch API.
Imports the FastAPI application instance.
"""

import sys
from pathlib import Path

# Ensure project root directory is added to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.main import app
