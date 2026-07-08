"""
Execution phase: runs each task in the plan sequentially.

Each task is given:
  - The original user request.
  - The full plan context (document type, objective, assumptions).
  - All outputs produced by prior tasks (accumulated context).

The executor updates task status and captures the LLM output for every step.
"""
import logging

from core.llm import call_llm
from agent.models import AgentTask, ExecutionPlan, TaskStatus

logger = logging.getLogger(__name__)

_TASK_PROMPT = """
You are executing step {task_id} of {total_tasks} in an autonomous document-creation pipeline.

=== USER REQUEST ===
{request}

=== DOCUMENT CONTEXT ===
Document Type : {doc_type}
Document Title: {doc_title}
Objective     : {objective}
Assumptions   : {assumptions}

=== PRIOR TASK OUTPUTS ===
{prior_context}

=== CURRENT TASK ===
ID         : {task_id}
Title      : {task_title}
Description: {task_description}

Instructions:
- Produce ONLY the content for this specific task — do not repeat prior sections.
- Use professional, formal business language.
- Where real data is unavailable, use realistic, plausible mock data (named people, dates, figures).
- Be thorough: the quality of your output directly determines the quality of the final document.
- Do NOT include meta-commentary like "Here is the output for task X". Just produce the content.
"""


def execute_plan(plan: ExecutionPlan, request: str) -> ExecutionPlan:
    """
    Execute all tasks in the plan sequentially.
    Each task's output becomes available as context to the next task.
    Updates plan in-place and returns it.
    """
    prior_context_parts: list[str] = []

    for task in plan.tasks:
        task.status = TaskStatus.IN_PROGRESS
        logger.info("Executing task %d/%d: '%s'", task.id, len(plan.tasks), task.title)

        prior_context = (
            "\n\n".join(prior_context_parts) if prior_context_parts else "None — this is the first task."
        )

        prompt = _TASK_PROMPT.format(
            task_id=task.id,
            total_tasks=len(plan.tasks),
            request=request,
            doc_type=plan.document_type,
            doc_title=plan.document_title,
            objective=plan.objective,
            assumptions="\n".join(f"- {a}" for a in plan.assumptions),
            prior_context=prior_context,
            task_title=task.title,
            task_description=task.description,
        )

        try:
            task.output = call_llm(prompt)
            task.status = TaskStatus.DONE
            prior_context_parts.append(f"[Task {task.id}: {task.title}]\n{task.output}")
            logger.info("Task %d complete (%d chars).", task.id, len(task.output))
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.output = f"[EXECUTION FAILED: {exc}]"
            logger.error("Task %d failed: %s", task.id, exc)

    return plan
