"""Pydantic schemas and data models for HackMate AI."""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class TaskPriority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class TaskStatus(str, Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    BLOCKED = "Blocked"
    DONE = "Done"


class BlockerStatus(str, Enum):
    ACTIVE = "Active"
    RESOLVED = "Resolved"


class ProposalStatus(str, Enum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"


class TeamMember(BaseModel):
    id: str = Field(..., description="Unique ID for team member (e.g., 'm1', 'm2')")
    name: str = Field(..., min_length=1, description="Full name or display name")
    role: str = Field(default="Developer", description="Role/specialization")
    skills: List[str] = Field(default_factory=list, description="List of technical skills")
    max_hours: float = Field(default=24.0, ge=1.0, description="Max available hackathon hours")
    current_workload_hours: float = Field(default=0.0, ge=0.0, description="Sum of active task hours")


class Task(BaseModel):
    id: str = Field(..., description="Unique task identifier, e.g., 'TASK-1'")
    title: str = Field(..., min_length=2, description="Short descriptive title")
    description: str = Field(default="", description="Detailed task requirements")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    assigned_to: str = Field(default="Unassigned", description="Name or ID of team member")
    estimated_hours: float = Field(default=2.0, ge=0.1, le=48.0, description="Estimated duration in hours")
    status: TaskStatus = Field(default=TaskStatus.TODO)
    dependencies: List[str] = Field(default_factory=list, description="IDs of prerequisite tasks")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Checklist for done")
    suggested_order: int = Field(default=1, ge=1, description="Suggested completion order")
    notes: str = Field(default="", description="Team notes or progress updates")
    is_mvp: bool = Field(default=True, description="Whether task is vital for MVP")

    @field_validator("id")
    @classmethod
    def normalize_id(cls, v: str) -> str:
        return v.strip().upper()


class Blocker(BaseModel):
    id: str = Field(..., description="Unique blocker ID, e.g., 'BLK-1'")
    task_id: Optional[str] = Field(default=None, description="Related task ID if applicable")
    reported_by: str = Field(default="System", description="Who reported this blocker")
    blocker_type: str = Field(
        default="Other",
        description="Type: Member Unavailable, API/Library Failure, Task Delayed, Missing Dependency, Integration Failure, Scope Creep, Other",
    )
    description: str = Field(..., min_length=3, description="Details of the blocker")
    is_inferred: bool = Field(
        default=False,
        description="True if inferred automatically from task metrics, False if explicitly reported by user",
    )
    status: BlockerStatus = Field(default=BlockerStatus.ACTIVE)
    resolution_steps: List[str] = Field(default_factory=list, description="Actionable recommended steps")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    resolved_at: Optional[str] = Field(default=None)


class ReplanProposal(BaseModel):
    id: str = Field(..., description="Proposal ID, e.g., 'PROP-1'")
    project_id: str = Field(..., description="Target project ID")
    summary: str = Field(..., description="Executive summary of the proposed adjustments")
    previous_tasks: List[Task] = Field(..., description="Snapshot of tasks before replanning")
    revised_tasks: List[Task] = Field(..., description="Proposed tasks after replanning")
    recommended_changes: List[str] = Field(default_factory=list, description="Bullet points of what changed")
    reasons: List[str] = Field(default_factory=list, description="Reasons behind the adjustments")
    risks_and_tradeoffs: List[str] = Field(default_factory=list, description="Key trade-offs or reduced scope")
    member_next_actions: Dict[str, str] = Field(
        default_factory=dict, description="Concrete immediate next action per member"
    )
    status: ProposalStatus = Field(default=ProposalStatus.PENDING)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ActivityLog(BaseModel):
    id: str = Field(..., description="Log ID")
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    action_type: str = Field(
        ...,
        description="PLAN_CREATED, TASK_UPDATED, BLOCKER_REPORTED, BLOCKER_RESOLVED, REPLAN_PROPOSED, REPLAN_ACCEPTED, REPLAN_REJECTED",
    )
    description: str = Field(..., description="Human readable description")
    author: str = Field(default="System", description="User or Agent name")


class Project(BaseModel):
    id: str = Field(..., description="Unique project ID")
    name: str = Field(..., min_length=1, description="Project name")
    idea: str = Field(..., description="Core project concept and problem statement")
    problem_statement: str = Field(default="", description="Expanded problem statement")
    category: str = Field(default="AI & Agents", description="Hackathon category")
    deadline_hours: float = Field(default=24.0, ge=1.0, description="Total hours for the hackathon")
    team_size: int = Field(default=2, ge=1, le=10, description="Number of members")
    team_members: List[TeamMember] = Field(default_factory=list)
    tasks: List[Task] = Field(default_factory=list)
    blockers: List[Blocker] = Field(default_factory=list)
    replan_proposals: List[ReplanProposal] = Field(default_factory=list)
    activity_logs: List[ActivityLog] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
