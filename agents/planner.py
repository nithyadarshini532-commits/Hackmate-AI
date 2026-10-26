"""Planner Agent: converts project ideas into structured, dependency-validated MVP task plans."""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from models.schemas import Task, TaskPriority, TaskStatus, TeamMember
from services.dependency_service import DependencyService
from services.ollama_service import OllamaService
from agents.assignment import AssignmentAgent

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are an expert AI Hackathon Project Manager and Technical Architect.
Your task is to take a hackathon project idea, category, team skills, and deadline hours, and generate a rock-solid, realistic Minimum Viable Product (MVP) task plan for a 2-person team.

Rules:
1. Prioritize a minimal viable core hackathon demo (MVP). Do not include unnecessary fluff.
2. Structure tasks with realistic durations (1 to 4 hours each). Total hours must fit within the deadline.
3. Every task must specify prerequisite dependencies using prior task IDs (e.g., 'TASK-1', 'TASK-2').
4. Include dedicated tasks for Architecture/Data Contract, Core Backend/AI, Frontend/UI, Integration Testing, and Pitch/Demo.
5. Strictly avoid circular dependencies! TASK-1 cannot depend on anything. Early tasks cannot depend on later tasks.
6. Return ONLY a valid JSON array of task objects matching the following schema:
[
  {
    "id": "TASK-1",
    "title": "Short title",
    "description": "Clear technical description",
    "priority": "High" | "Medium" | "Low",
    "assigned_to": "Team Member Name" | "Unassigned",
    "estimated_hours": 2.5,
    "dependencies": [],
    "acceptance_criteria": ["Item 1", "Item 2"],
    "suggested_order": 1,
    "is_mvp": true
  }
]
Do not include any conversational preamble or markdown other than the JSON block.
"""


class PlannerAgent:
    def __init__(self, ollama: Optional[OllamaService] = None):
        self.ollama = ollama or OllamaService()

    def generate_plan(
        self,
        name: str,
        idea: str,
        problem_statement: str,
        category: str,
        deadline_hours: float,
        team_members: List[TeamMember],
        model: Optional[str] = None,
        turbo_mode: bool = False,
    ) -> Tuple[List[Task], str, bool]:
        """Generates a structured task plan.

        Returns: (tasks, message_or_source, is_real_ai)
        """
        # If Turbo Mode is requested, generate instant deterministic heuristic plan (<50ms)
        if turbo_mode:
            fallback_tasks = self._generate_heuristic_plan(
                name, idea, problem_statement, category, deadline_hours, team_members
            )
            AssignmentAgent.balance_and_assign_tasks(fallback_tasks, team_members)
            return (
                fallback_tasks,
                f"Generated instantly via HackMate AI Turbo Engine ({len(fallback_tasks)} tasks in <50ms).",
                False,
            )

        members_summary = ", ".join(
            [f"{m.name} ({m.role}: skills={', '.join(m.skills)})" for m in team_members]
        )

        user_prompt = f"""Generate an MVP project task plan for this hackathon:
Project Name: {name}
Category: {category}
Idea & Problem: {idea}
Expanded Problem Statement: {problem_statement or 'N/A'}
Deadline / Total Available Hours: {deadline_hours} hours
Team Size: {len(team_members)}
Team Members: {members_summary}

Create 6 to 8 prioritized tasks with clean sequential dependencies, realistic durations, and clear acceptance criteria."""

        # Check if Ollama is accessible
        health = self.ollama.check_health()
        if health["connected"]:
            logger.info("Ollama is reachable, calling LLM for project plan...")
            success, raw_response = self.ollama.generate_chat(
                messages=[
                    {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                model=model,
                temperature=0.2,
                timeout=50.0,
            )

            if success:
                extracted = self.ollama.extract_json(raw_response)
                if isinstance(extracted, list) and len(extracted) > 0:
                    parsed_tasks = self._parse_tasks_from_json(extracted, team_members)
                    if parsed_tasks:
                        # Validate dependencies and repair if needed
                        repaired_tasks = self._sanitize_and_repair_dependencies(parsed_tasks)
                        # Rebalance assignments
                        AssignmentAgent.balance_and_assign_tasks(repaired_tasks, team_members)
                        return (
                            repaired_tasks,
                            f"Generated {len(repaired_tasks)} tasks via Ollama ({model or self.ollama.default_model}).",
                            True,
                        )

            logger.warning(f"Ollama response could not be parsed: {raw_response[:200]}...")

        # Fallback Heuristic Generator (Demo/Offline Mode)
        fallback_tasks = self._generate_heuristic_plan(
            name, idea, problem_statement, category, deadline_hours, team_members
        )
        AssignmentAgent.balance_and_assign_tasks(fallback_tasks, team_members)
        reason = (
            "Generated using HackMate AI Smart Heuristic Engine (Ollama server offline or model not found)."
            if not health["connected"]
            else "Generated using HackMate AI Smart Heuristic Engine (Ollama output formatted as fallback)."
        )
        return fallback_tasks, reason, False

    def _parse_tasks_from_json(
        self, raw_list: List[Dict[str, Any]], team_members: List[TeamMember]
    ) -> List[Task]:
        """Converts raw json dicts into validated Task objects."""
        tasks: List[Task] = []
        valid_member_names = {m.name for m in team_members}

        for idx, item in enumerate(raw_list):
            if not isinstance(item, dict):
                continue

            tid = str(item.get("id") or f"TASK-{idx + 1}").strip().upper()
            title = str(item.get("title") or f"Task {idx + 1}").strip()
            desc = str(item.get("description") or "").strip()

            prio_raw = str(item.get("priority", "Medium")).capitalize()
            prio = TaskPriority.MEDIUM
            if prio_raw in ("High", "Low"):
                prio = TaskPriority(prio_raw)

            assigned = str(item.get("assigned_to", "Unassigned")).strip()
            if assigned not in valid_member_names:
                assigned = "Unassigned"

            try:
                hours = float(item.get("estimated_hours", 2.0))
                hours = max(0.5, min(hours, 24.0))
            except Exception:
                hours = 2.0

            deps_raw = item.get("dependencies") or []
            if isinstance(deps_raw, list):
                deps = [str(d).strip().upper() for d in deps_raw if str(d).strip().upper() != tid]
            else:
                deps = []

            criteria_raw = item.get("acceptance_criteria") or []
            criteria = (
                [str(c).strip() for c in criteria_raw if str(c).strip()]
                if isinstance(criteria_raw, list)
                else ["Meets specification"]
            )

            order = item.get("suggested_order") or (idx + 1)
            try:
                order = int(order)
            except Exception:
                order = idx + 1

            tasks.append(
                Task(
                    id=tid,
                    title=title,
                    description=desc,
                    priority=prio,
                    assigned_to=assigned,
                    estimated_hours=hours,
                    status=TaskStatus.TODO,
                    dependencies=deps,
                    acceptance_criteria=criteria,
                    suggested_order=order,
                    notes="",
                    is_mvp=bool(item.get("is_mvp", True)),
                )
            )

        return tasks

    def _sanitize_and_repair_dependencies(self, tasks: List[Task]) -> List[Task]:
        """Detects invalid IDs or cycles and automatically cleans them."""
        task_id_set = {t.id.upper() for t in tasks}
        # 1. Strip missing dependencies
        for t in tasks:
            t.dependencies = [dep for dep in t.dependencies if dep in task_id_set and dep != t.id]

        # 2. Check for cycles and break them safely
        validation = DependencyService.validate_dependencies(tasks)
        if not validation.is_valid and validation.cycles:
            for cycle in validation.cycles:
                if len(cycle) >= 2:
                    # Break dependency from cycle[0] to cycle[1]
                    t_from = next((t for t in tasks if t.id.upper() == cycle[0]), None)
                    if t_from and cycle[1] in t_from.dependencies:
                        t_from.dependencies.remove(cycle[1])

        return tasks

    def _generate_heuristic_plan(
        self,
        name: str,
        idea: str,
        problem_statement: str,
        category: str,
        deadline_hours: float,
        team_members: List[TeamMember],
    ) -> List[Task]:
        """Deterministic smart plan generator when Ollama is offline."""
        m1 = team_members[0].name if len(team_members) > 0 else "Member 1"
        m2 = team_members[1].name if len(team_members) > 1 else m1

        # Heuristic scaled tasks
        total_scale = max(0.5, deadline_hours / 24.0)

        tasks = [
            Task(
                id="TASK-1",
                title="Architecture & API Contract Design",
                description=f"Define project architecture, data contracts, and component schemas for {name}.",
                priority=TaskPriority.HIGH,
                assigned_to=m1,
                estimated_hours=round(2.0 * total_scale, 1),
                status=TaskStatus.TODO,
                dependencies=[],
                acceptance_criteria=[
                    "Core data schemas defined in Pydantic/JSON",
                    "Component interfaces agreed between team members",
                ],
                suggested_order=1,
                is_mvp=True,
            ),
            Task(
                id="TASK-2",
                title=f"Core Backend & {category} Engine",
                description=f"Implement backend logic, core processing pipelines, and data models for {name}.",
                priority=TaskPriority.HIGH,
                assigned_to=m2,
                estimated_hours=round(3.5 * total_scale, 1),
                status=TaskStatus.TODO,
                dependencies=["TASK-1"],
                acceptance_criteria=[
                    "Primary algorithmic pipeline functional",
                    "Outputs verified against defined schema",
                ],
                suggested_order=2,
                is_mvp=True,
            ),
            Task(
                id="TASK-3",
                title="Frontend Layout & Interactive Dashboard",
                description="Build Streamlit user interface, navigation, responsive controls, and visual cards.",
                priority=TaskPriority.HIGH,
                assigned_to=m1,
                estimated_hours=round(4.0 * total_scale, 1),
                status=TaskStatus.TODO,
                dependencies=["TASK-1"],
                acceptance_criteria=[
                    "Modern dark theme with responsive layout",
                    "Forms and action controls wired to state",
                ],
                suggested_order=3,
                is_mvp=True,
            ),
            Task(
                id="TASK-4",
                title="AI Integration & Inference Engine",
                description="Connect local AI/Ollama endpoints and handle prompt generation and JSON validation.",
                priority=TaskPriority.HIGH,
                assigned_to=m2,
                estimated_hours=round(3.5 * total_scale, 1),
                status=TaskStatus.TODO,
                dependencies=["TASK-2"],
                acceptance_criteria=[
                    "Model responses parsed and validated against schema",
                    "Graceful fallback handling when offline",
                ],
                suggested_order=4,
                is_mvp=True,
            ),
            Task(
                id="TASK-5",
                title="Analytics & Telemetry Visualization",
                description="Add charts, progress tracking meters, and real-time operational feedback views.",
                priority=TaskPriority.MEDIUM,
                assigned_to=m1,
                estimated_hours=round(2.5 * total_scale, 1),
                status=TaskStatus.TODO,
                dependencies=["TASK-3"],
                acceptance_criteria=[
                    "Visual charts rendering real metrics",
                    "Interactive filters operational",
                ],
                suggested_order=5,
                is_mvp=True,
            ),
            Task(
                id="TASK-6",
                title="End-to-End System Integration & Testing",
                description="Connect UI with backend and AI pipeline. Run automated pytest test suite.",
                priority=TaskPriority.HIGH,
                assigned_to=m1,
                estimated_hours=round(3.0 * total_scale, 1),
                status=TaskStatus.TODO,
                dependencies=["TASK-3", "TASK-4", "TASK-5"],
                acceptance_criteria=[
                    "Complete end-to-end user workflow validated",
                    "Pytest suite passing without failures",
                ],
                suggested_order=6,
                is_mvp=True,
            ),
            Task(
                id="TASK-7",
                title="Pitch Deck & Final Demo Walkthrough",
                description="Prepare demonstration script, slide deck, and timing rehearsals for hackathon judges.",
                priority=TaskPriority.MEDIUM,
                assigned_to=m2,
                estimated_hours=round(2.0 * total_scale, 1),
                status=TaskStatus.TODO,
                dependencies=["TASK-6"],
                acceptance_criteria=[
                    "3-minute pitch deck completed",
                    "Live demo flow rehearsed and timed",
                ],
                suggested_order=7,
                is_mvp=False,
            ),
        ]

        return tasks
