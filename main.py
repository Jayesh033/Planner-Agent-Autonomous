"""
Entry point for the Autonomous Agent API.

Run:
    uvicorn main:app --reload --port 8000
"""
import logging
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from core.config import settings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  —  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Autonomous AI Agent",
    description=(
        "An autonomous agent that understands natural language requests, "
        "builds its own execution plan, executes each step with Gemini, "
        "self-reflects on quality, and produces a polished Word document."
    ),
    version="1.0.0",
    contact={"name": "Jayesh", "email": "aditi.s.bhangre@gmail.com"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
