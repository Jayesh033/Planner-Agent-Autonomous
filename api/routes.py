"""
FastAPI routes for the autonomous agent API.
"""
import base64
import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from agent import pipeline

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AgentRequest(BaseModel):
    request: Annotated[str, Field(min_length=10, max_length=2000, description="Natural language request")]

    @field_validator("request")
    @classmethod
    def validate_request(cls, v: str) -> str:
        v = v.strip()
        # Guardrail: reject obviously non-business requests
        banned_keywords = {"hack", "exploit", "malware", "illegal", "password", "crack"}
        lower = v.lower()
        if any(kw in lower for kw in banned_keywords):
            raise ValueError("Request contains disallowed content.")
        if len(v.split()) < 3:
            raise ValueError("Request is too vague. Please provide more detail.")
        return v


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/agent",
    summary="Run the autonomous agent",
    description=(
        "Accepts a natural-language request, autonomously plans and executes tasks, "
        "self-reflects on quality, and returns a polished Microsoft Word document."
    ),
    response_description="Agent execution result with base64-encoded Word document",
)
async def run_agent(body: AgentRequest) -> JSONResponse:
    logger.info("POST /agent — request: %.80s…", body.request)
    try:
        result = pipeline.run(body.request)
        return JSONResponse(content=result.model_dump())
    except ValueError as exc:
        logger.warning("Validation error: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Pipeline error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Agent pipeline failed: {exc}")


@router.post(
    "/agent/download",
    summary="Run agent and return the Word document directly",
    description="Same as /agent but streams the .docx file as a download instead of JSON.",
    response_class=Response,
)
async def run_agent_download(body: AgentRequest) -> Response:
    logger.info("POST /agent/download — request: %.80s…", body.request)
    try:
        result = pipeline.run(body.request)
        doc_bytes = base64.b64decode(result.document_base64)
        return Response(
            content=doc_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{result.document_filename}"'},
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Pipeline error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Agent pipeline failed: {exc}")


@router.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok", "service": "autonomous-agent"}
