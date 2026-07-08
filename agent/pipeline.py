"""
Top-level agent pipeline: orchestrates Plan → Execute → Reflect → Build.

This is the single entry point for the agent; the FastAPI route only calls run().
"""
import base64
import logging
import uuid
from pathlib import Path

from core.config import settings
from agent.planner import build_plan
from agent.executor import execute_plan
from agent.reflector import reflect_and_revise
from agent.doc_builder import build_document
from agent.models import AgentResponse, TaskStatus

logger = logging.getLogger(__name__)


def run(request: str) -> AgentResponse:
    """
    Full agent pipeline for a single user request.

    Stages:
      1. Plan   — LLM generates a structured task list.
      2. Execute — Each task is run in order; outputs accumulate as context.
      3. Reflect — LLM self-reviews quality; weak sections are revised.
      4. Build  — python-docx assembles the final Word document.

    Returns an AgentResponse containing metadata and the document as base64.
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Agent pipeline started.", request_id)

    # ── Stage 1: Plan ────────────────────────────────────────────────────────
    plan = build_plan(request)

    # ── Stage 2: Execute ─────────────────────────────────────────────────────
    plan = execute_plan(plan, request)

    failed = [t for t in plan.tasks if t.status == TaskStatus.FAILED]
    if failed:
        logger.warning("[%s] %d task(s) failed: %s", request_id, len(failed), [t.title for t in failed])

    # ── Stage 3: Reflect ─────────────────────────────────────────────────────
    reflection = reflect_and_revise(plan)

    # ── Stage 4: Build document ───────────────────────────────────────────────
    doc_path = build_document(plan, reflection, settings.output_dir)

    # Encode document as base64 for API transport
    doc_bytes = doc_path.read_bytes()
    doc_b64 = base64.b64encode(doc_bytes).decode("utf-8")

    logger.info("[%s] Pipeline complete. Doc: %s (%d bytes)", request_id, doc_path.name, len(doc_bytes))

    return AgentResponse(
        request_id=request_id,
        original_request=request,
        document_type=plan.document_type,
        document_title=plan.document_title,
        objective=plan.objective,
        assumptions=plan.assumptions,
        tasks=[t.model_dump() for t in plan.tasks],
        reflection=reflection.model_dump(),
        document_filename=doc_path.name,
        document_base64=doc_b64,
        status="success" if reflection.passed else "completed_with_warnings",
        message=(
            "Document generated successfully."
            if reflection.passed
            else f"Document generated with quality warnings: {'; '.join(reflection.gaps)}"
        ),
    )
