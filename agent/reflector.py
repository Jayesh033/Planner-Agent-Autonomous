"""
Reflection phase: the agent reviews its own work and optionally revises weak sections.

This implements the 'Multi-step planning + Reflection' engineering improvement.

Why reflection matters:
  - Catches missing sections, shallow content, or inconsistencies before the doc is built.
  - Produces a quality score that surfaces in the API response.
  - Allows targeted re-generation of weak sections without re-running the whole pipeline.

The reflector acts as a senior editor who has NOT seen the original request — it judges
only on the quality and completeness of the produced content.
"""
import logging

from core.llm import call_llm_json
from agent.models import ExecutionPlan, ReflectionResult, TaskStatus

logger = logging.getLogger(__name__)

_REFLECT_PROMPT = """
You are a senior editor reviewing AI-generated content for a professional business document.

=== DOCUMENT METADATA ===
Type     : {doc_type}
Title    : {doc_title}
Objective: {objective}

=== TASK OUTPUTS TO REVIEW ===
{task_outputs}

Evaluate the content critically and return ONLY valid JSON matching this schema:
{{
  "passed": true,
  "score": 8,
  "gaps": ["<gap 1>", "<gap 2>"],
  "improvements": ["<improvement suggestion 1>"],
  "revised_sections": {{
    "3": "<full revised content for task id 3 if it needs improvement>"
  }}
}}

Scoring rubric (0–10):
  10 — publication-ready, no gaps
   8 — professional quality, minor improvements possible
   6 — acceptable but thin in places
   4 — significant gaps or shallow content
   2 — fails to address the objective

Rules:
- "passed" is true if score >= 6.
- "gaps" lists specific missing facts or sections (empty list if none).
- "improvements" lists actionable suggestions (empty list if none).
- "revised_sections" — if score < 8, provide improved content for the weakest task(s).
  Use the task id (as a string) as the key. Only include tasks that genuinely need revision.
  Leave empty if no revision is needed.
- Be strict but fair. A good document that uses appropriate mock data should score >= 7.
"""

_REVISE_PROMPT = """
You are rewriting a section of a professional {doc_type} document.

Document Title: {doc_title}
Original section (Task {task_id} — {task_title}):
\"\"\"
{original_output}
\"\"\"

Editor feedback:
{feedback}

Produce an improved version of this section. Be thorough and professional.
Do NOT include any meta-commentary — output only the revised content.
"""


def reflect_and_revise(plan: ExecutionPlan) -> ReflectionResult:
    """
    Review all task outputs and revise weak sections.
    Returns a ReflectionResult; also updates plan tasks in-place with revised content.
    """
    logger.info("Reflection phase started.")

    task_outputs = "\n\n".join(
        f"--- Task {t.id}: {t.title} ---\n{t.output}"
        for t in plan.tasks
        if t.status == TaskStatus.DONE
    )

    prompt = _REFLECT_PROMPT.format(
        doc_type=plan.document_type,
        doc_title=plan.document_title,
        objective=plan.objective,
        task_outputs=task_outputs,
    )

    data = call_llm_json(prompt)
    result = ReflectionResult(**data)

    logger.info(
        "Reflection complete — score: %d/10, passed: %s, gaps: %d",
        result.score,
        result.passed,
        len(result.gaps),
    )

    # Apply any revised sections back into the plan
    if result.revised_sections:
        task_map = {str(t.id): t for t in plan.tasks}
        for task_id_str, revised_content in result.revised_sections.items():
            if task_id_str in task_map and revised_content.strip():
                task = task_map[task_id_str]
                logger.info("Applying revision to task %s: '%s'", task_id_str, task.title)
                task.output = revised_content
            else:
                logger.warning("Revision references unknown task id '%s', skipping.", task_id_str)

    return result
