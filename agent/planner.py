"""
Planning phase: converts a user request into a structured ExecutionPlan.

The planner asks the LLM to:
  1. Identify what type of document best fits the request.
  2. Determine what information is needed.
  3. Make reasonable assumptions for anything missing.
  4. Break the work into discrete, ordered tasks.
"""
import logging

from core.llm import call_llm_json
from agent.models import AgentTask, ExecutionPlan

logger = logging.getLogger(__name__)

_PLAN_PROMPT = """
You are a senior business analyst and document architect.

A user has submitted the following request:
\"\"\"
{request}
\"\"\"

Your job is to create a detailed execution plan for an autonomous AI agent that will:
  - Produce a polished Microsoft Word document fulfilling this request.
  - Make reasonable, professional assumptions where information is missing.
  - Use realistic mock data where real data is unavailable.

Return ONLY valid JSON matching this exact schema (no markdown, no explanation):
{{
  "document_type": "<e.g. Project Proposal, Business Report, Meeting Minutes, SOP, Technical Design>",
  "document_title": "<professional title for the document>",
  "objective": "<one concise sentence describing the goal>",
  "assumptions": ["<assumption 1>", "<assumption 2>"],
  "tasks": [
    {{
      "id": 1,
      "title": "<short task name>",
      "description": "<what this step produces and why it is needed>",
      "status": "pending",
      "output": ""
    }}
  ]
}}

Rules:
- Include 4 to 7 tasks. Each task must produce a distinct section or piece of content.
- Tasks must be ordered so later tasks can reference earlier outputs.
- Task 1 is always "Context & Requirements Gathering" — extract key facts from the request.
- The final task is always "Final Review & Compilation" — consolidate all prior outputs.
- Use professional business language.
- List every assumption the agent is making (minimum 2, maximum 6).
"""


def build_plan(request: str) -> ExecutionPlan:
    """Generate a structured execution plan from a natural-language request."""
    logger.info("Planning phase started.")
    prompt = _PLAN_PROMPT.format(request=request)
    data = call_llm_json(prompt)

    tasks = [AgentTask(**t) for t in data["tasks"]]
    plan = ExecutionPlan(
        document_type=data["document_type"],
        document_title=data["document_title"],
        objective=data["objective"],
        assumptions=data.get("assumptions", []),
        tasks=tasks,
    )
    logger.info(
        "Plan created: '%s' (%d tasks, type=%s)",
        plan.document_title,
        len(plan.tasks),
        plan.document_type,
    )
    return plan
