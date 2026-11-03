"""Vercel entrypoint (E5.4): Vercel looks for `app` in a root `app.py`."""
from src.api.server import app

__all__ = ["app"]
