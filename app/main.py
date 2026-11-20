"""Vercel entrypoint — re-export the FastAPI app from api.server."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.server import app
