"""Replanning Agent: generates revised schedules, scope reductions, and workload adjustments with user approval."""
import copy
from datetime import datetime
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from models.schemas import (
    BlockerStatus,
    Project,
    ProposalStatus,
    ReplanProposal,
    Task,
    TaskPriority,
    TaskStatus,
)
from services.dependency_service import DependencyService
from services.ollama_service import OllamaService
from agents.assignment import AssignmentAgent

logger = logging.getLogger(__name__)

REPLAN_SYSTEM_PROMPT = """You are an expert AI Hackathon Replanning Agent.
The hackathon team is facing blockers, scope creep, or timeline pressure.
Your job is to analyze the current tasks and blockers, and generate an updated, realistic revised task plan.

You must return ONLY a valid JSON object matching this structure:
{
  "summary": "Executive summary of the changes",
  "recommended_changes": [
    "Specific change 1",
    "Specific change 2"
  ],
  "reasons": [
    "Reason for change 1",
    "Reason for change 2"
  ],
  "risks_and_tradeoffs": [
    "Risk or tradeoff 1",
    "Risk or tradeoff 2"
  ],
  "member_next_actions": {
    "Member Name 1": "Immediate next action",
    "Member Name 2": "Immediate next action"
  },
  "revised_tasks": [
    {
      "id": "TASK-1",
      "title": "Title",
      "description": "Description",
      "priority": "High" | "Medium" | "Low",
      "assigned_to": "Member Name",
      "estimated_hours": 2.0,
      "status": "To Do" | "In Progress" | "Blocked" | "Done",
      "dependencies": [],
      "acceptance_criteria": ["Item 1"],
      "suggested_order": 1,
      "is_mvp": true
    }
  ]
}
Do not output conversational markdown outside the JSON object.
"""


class ReplanningAgent:
    def __init__(self, ollama: Optional[OllamaService] = None):
        self.ollama = ollama or OllamaService()

    def generate_replan(
        self,
        project: Project,
        model: Optional[str] = None,
        turbo_mode: bool = False,
    ) -> ReplanProposal:
        """Analyzes blockers and schedule, generating a staged ReplanProposal for user review."""
        proposal_id = f"PROP-{uuid.uuid4().hex[:6].upper()}"

        # If Turbo Mode is enabled, immediately compute optimal graph replan (<50ms)
        if turbo_mode:
            return self._generate_deterministic_replan(project, proposal_id)

        # Check if Ollama is connected
        health = self.ollama.check_health()
        if health["connected"]:
            logger.info("Calling Ollama for replan proposal...")
            tasks_json = json.dumps([t.model_dump() for t in project.tasks], indent=2)
            blockers_summary = "; ".join(
                [
                    f"[{b.id} on {b.task_id or 'general'}]: {b.description}"
                    for b in project.blockers
                    if b.status == BlockerStatus.ACTIVE
                ]
            )

            user_prompt = f"""Project: {project.name}
Deadline remaining: {project.deadline_hours} hours
Active Blockers: {blockers_summary or 'None explicitly reported'}
Current Tasks:
{tasks_json}

Create a revised plan that descope blockers, protects the core hackathon MVP, balances workload, and gets the project submitted on time."""

            success, raw_resp = self.ollama.generate_chat(
                messages=[
                    {"role": "system", "content": REPLAN_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                model=model,
                temperature=0.2,
                timeout=50.0,
            )

            if success:
                extracted = self.ollama.extract_json(raw_resp)
                if isinstance(extracted, dict) and "revised_tasks" in extracted:
                    parsed_proposal = self._parse_llm_proposal(
                        extracted, project, proposal_id
                    )
                    if parsed_proposal:
                        return parsed_proposal

        # Fallback Deterministic Replanning Engine
        return self._generate_deterministic_replan(project, proposal_id)

    def _parse_llm_proposal(
        self, data: Dict[str, Any], project: Project, proposal_id: str
    ) -> Optional[ReplanProposal]:
        """Validates and constructs ReplanProposal from LLM JSON output."""
        try:
            revised_tasks_raw = data.get("revised_tasks", [])
            revised_tasks: List[Task] = []
            for item in revised_tasks_raw:
                prio_str = str(item.get("priority", "Medium")).capitalize()
                prio = TaskPriority.MEDIUM
                if prio_str in ("High", "Low"):
                    prio = TaskPriority(prio_str)

                stat_str = str(item.get("status", "To Do"))
                stat = TaskStatus.TODO
                for s in TaskStatus:
                    if s.value.lower() == stat_str.lower():
                        stat = s
                        break

                revised_tasks.append(
                    Task(
                        id=str(item.get("id")).strip().upper(),
                        title=str(item.get("title")).strip(),
                        description=str(item.get("description", "")).strip(),
                        priority=prio,
                        assigned_to=str(item.get("assigned_to", "Unassigned")).strip(),
                        estimated_hours=float(item.get("estimated_hours", 2.0)),
                        status=stat,
                        dependencies=[str(d).strip().upper() for d in item.get("dependencies", [])],
                        acceptance_criteria=item.get("acceptance_criteria", ["Meets spec"]),
                        suggested_order=int(item.get("suggested_order", 1)),
                        notes=str(item.get("notes", "")),
                        is_mvp=bool(item.get("is_mvp", True)),
                    )
                )

            # Validate dependencies
            val = DependencyService.validate_dependencies(revised_tasks)
            if not val.is_valid:
                # Fall back to deterministic if LLM generated invalid graph
                return None

            return ReplanProposal(
                id=proposal_id,
                project_id=project.id,
                summary=str(data.get("summary", "AI Generated Replan Proposal")),
                previous_tasks=copy.deepcopy(project.tasks),
                revised_tasks=revised_tasks,
                recommended_changes=data.get("recommended_changes", []),
                reasons=data.get("reasons", []),
                risks_and_tradeoffs=data.get("risks_and_tradeoffs", []),
                member_next_actions=data.get("member_next_actions", {}),
                status=ProposalStatus.PENDING,
                created_at=datetime.now().isoformat(),
            )
        except Exception as e:
            logger.warning(f"Failed to parse LLM replan: {e}")
            return None

    def _generate_deterministic_replan(
        self, project: Project, proposal_id: str
    ) -> ReplanProposal:
        """Deterministic, highly realistic replanning algorithm."""
        previous_tasks = copy.deepcopy(project.tasks)
        revised_tasks = copy.deepcopy(project.tasks)
        active_blockers = [b for b in project.blockers if b.status == BlockerStatus.ACTIVE]

        blocked_task_ids = {
            b.task_id.upper() for b in active_blockers if b.task_id
        }.union({t.id.upper() for t in revised_tasks if t.status == TaskStatus.BLOCKED})

        recommended_changes: List[str] = []
        reasons: List[str] = []
        risks_and_tradeoffs: List[str] = []

        # 1. Descope or decouple blocked tasks
        for t in revised_tasks:
            if t.id.upper() in blocked_task_ids:
                t.is_mvp = False
                t.priority = TaskPriority.LOW
                t.title = f"{t.title} (Descoped from MVP)"
                t.notes = "Descoped to stretch goal due to active blocker."
                recommended_changes.append(
                    f"Descoped [{t.id}] '{t.title}' from core MVP to stretch goal to avoid missing deadline."
                )
                reasons.append(
                    f"Task [{t.id}] has an active blocker preventing progress on downstream deliverables."
                )

        # 2. Unlink downstream tasks waiting on blocked tasks
        for t in revised_tasks:
            if t.id.upper() not in blocked_task_ids and t.status != TaskStatus.DONE:
                intersect = [dep for dep in t.dependencies if dep.upper() in blocked_task_ids]
                if intersect:
                    t.dependencies = [
                        dep for dep in t.dependencies if dep.upper() not in blocked_task_ids
                    ]
                    t.notes += f" Unlinked blocked prerequisite(s): {', '.join(intersect)} (using mock/synthetic data)."
                    recommended_changes.append(
                        f"Unlinked blocked dependencies ({', '.join(intersect)}) from [{t.id}] '{t.title}'. Switched to mock data contract."
                    )
                    reasons.append(
                        f"Unblocking [{t.id}] enables parallel progress toward the live hackathon demo."
                    )

        # 3. Workload balancing across the two members
        members = project.team_members
        if len(members) >= 2:
            m1_name, m2_name = members[0].name, members[1].name
            m1_hours = sum(
                t.estimated_hours
                for t in revised_tasks
                if t.assigned_to == m1_name and t.status != TaskStatus.DONE
            )
            m2_hours = sum(
                t.estimated_hours
                for t in revised_tasks
                if t.assigned_to == m2_name and t.status != TaskStatus.DONE
            )

            # If heavily imbalanced (> 4 hours difference)
            if abs(m1_hours - m2_hours) > 4.0:
                overloaded = m1_name if m1_hours > m2_hours else m2_name
                underloaded = m2_name if overloaded == m1_name else m1_name
                # Move one To Do task to underloaded member
                candidate = next(
                    (
                        t
                        for t in revised_tasks
                        if t.assigned_to == overloaded
                        and t.status == TaskStatus.TODO
                        and t.is_mvp
                    ),
                    None,
                )
                if candidate:
                    candidate.assigned_to = underloaded
                    recommended_changes.append(
                        f"Reassigned [{candidate.id}] '{candidate.title}' from {overloaded} to {underloaded} to balance hackathon workload."
                    )
                    reasons.append(
                        f"{overloaded} was carrying an excessive active workload ({max(m1_hours, m2_hours):.1f}h)."
                    )

        # Risks and trade-offs
        if blocked_task_ids:
            risks_and_tradeoffs.append(
                "Trade-off: Core presentation will rely on mock/synthetic components rather than physical hardware or problematic third-party API."
            )
            risks_and_tradeoffs.append(
                "Benefit: Guarantees end-to-end demo stability and avoids crashing in front of hackathon judges."
            )
        else:
            risks_and_tradeoffs.append(
                "Streamlined schedule leaves adequate buffer for final pitch rehearsals."
            )

        # Clear next actions per member
        member_next_actions: Dict[str, str] = {}
        for m in project.team_members:
            # Find next ready task for member
            next_task = next(
                (
                    t
                    for t in revised_tasks
                    if t.assigned_to == m.name
                    and t.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS)
                    and DependencyService.get_task_readiness(t, revised_tasks).is_ready
                ),
                None,
            )
            if next_task:
                member_next_actions[m.name] = (
                    f"Work on [{next_task.id}] '{next_task.title}' ({next_task.estimated_hours}h estimated)."
                )
            else:
                member_next_actions[m.name] = (
                    "Assist teammate with integration testing and start drafting the 3-minute pitch deck."
                )

        summary = (
            f"Revised plan with {len(recommended_changes)} adjustments: descoped high-risk blockers, "
            f"switched to mock data contracts to unblock integration, and rebalanced team workload."
        )

        return ReplanProposal(
            id=proposal_id,
            project_id=project.id,
            summary=summary,
            previous_tasks=previous_tasks,
            revised_tasks=revised_tasks,
            recommended_changes=recommended_changes,
            reasons=reasons,
            risks_and_tradeoffs=risks_and_tradeoffs,
            member_next_actions=member_next_actions,
            status=ProposalStatus.PENDING,
            created_at=datetime.now().isoformat(),
        )
