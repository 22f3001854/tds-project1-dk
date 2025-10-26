"""
TDS Project 1 - Application Entry Point

This module imports the FastAPI application from main.py.
Used for deployment scenarios where the app variable needs to be
accessible at the module level (e.g., Gunicorn, Uvicorn workers).

Usage:
    uvicorn app:app --host 0.0.0.0 --port 7860
"""

from main import app

# Export the app instance for ASGI servers
__all__ = ["app"]