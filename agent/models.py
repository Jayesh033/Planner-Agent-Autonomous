"""
Shared Pydantic models used across the agent pipeline.
"""
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


class AgentTask(BaseModel):
    id: int
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    output: str = ""


class ExecutionPlan(BaseModel):
    document_type: str = Field(description="Type of document to produce, e.g. 'Project Proposal'")
    document_title: str
    objective: str = Field(description="One-sentence goal of the request")
    assumptions: list[str] = Field(default_factory=list)
    tasks: list[AgentTask]


class ReflectionResult(BaseModel):
    passed: bool
    score: int = Field(ge=0, le=10, description="Quality score 0-10")
    gaps: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    revised_sections: dict[str, str] = Field(
        default_factory=dict,
        description="task_id -> improved content for sections that need revision",
    )


class AgentResponse(BaseModel):
    request_id: str
    original_request: str
    document_type: str
    document_title: str
    objective: str
    assumptions: list[str]
    tasks: list[dict[str, Any]]
    reflection: dict[str, Any]
    document_filename: str
    document_base64: str
    status: str = "success"
    message: str = ""
