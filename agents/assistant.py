"""AI Project Assistant Agent: project-aware chat assistant grounded strictly in current state."""
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
from models.schemas import BlockerStatus, Project, TaskStatus
from services.dependency_service import DependencyService
from services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

ASSISTANT_SYSTEM_PROMPT = """You are HackMate AI Assistant, an elite agile project manager for hackathons.
Your primary directive is to be grounded 100% in the factual project data provided below.
DO NOT hallucinate task statuses. DO NOT claim work has been done unless status is explicitly 'Done'.
Be concise, actionable, and encouraging. Use bullet points and refer to tasks by their IDs (e.g., [TASK-1]).

Current Project Data:
{project_context}
"""


class ProjectAssistantAgent:
    def __init__(self, ollama: Optional[OllamaService] = None):
        self.ollama = ollama or OllamaService()

    def build_project_context(self, project: Project) -> str:
        """Constructs an accurate textual snapshot of the project."""
        lines: List[str] = [
            f"Project: {project.name} ({project.category})",
            f"Idea: {project.idea}",
            f"Deadline Total Hours: {project.deadline_hours}h",
            "Team Members:",
        ]
        for m in project.team_members:
            lines.append(
                f"- {m.name} | Role: {m.role} | Skills: {', '.join(m.skills)} | Active Workload: {m.current_workload_hours:.1f}h"
            )

        lines.append("\nTasks:")
        for t in project.tasks:
            deps_str = f" [Dependencies: {', '.join(t.dependencies)}]" if t.dependencies else ""
            readiness = DependencyService.get_task_readiness(t, project.tasks)
            ready_label = "READY" if readiness.is_ready else f"WAITING ({readiness.reason})"
            lines.append(
                f"- [{t.id}] {t.title} | Status: {t.status.value} | Assigned: {t.assigned_to} | Est: {t.estimated_hours}h | Order: {t.suggested_order} | MVP: {t.is_mvp} | {ready_label}{deps_str}"
            )

        active_blockers = [b for b in project.blockers if b.status == BlockerStatus.ACTIVE]
        lines.append(f"\nActive Blockers ({len(active_blockers)}):")
        for b in active_blockers:
            inferred_str = " (Inferred Risk)" if b.is_inferred else " (User Reported)"
            lines.append(
                f"- [{b.id} on {b.task_id or 'General'}{inferred_str}] By: {b.reported_by} | Type: {b.blocker_type} | Details: {b.description}"
            )

        return "\n".join(lines)

    def answer_query(
        self,
        project: Project,
        user_query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        turbo_mode: bool = False,
    ) -> str:
        """Answers a project query using Ollama if available, or smart deterministic answers if offline or in turbo mode."""
        if turbo_mode:
            return self._generate_grounded_fallback(project, user_query)

        context = self.build_project_context(project)
        health = self.ollama.check_health()

        if health["connected"]:
            system_msg = ASSISTANT_SYSTEM_PROMPT.format(project_context=context)
            messages = [{"role": "system", "content": system_msg}]

            # Add recent history
            if conversation_history:
                for msg in conversation_history[-6:]:
                    messages.append(msg)

            messages.append({"role": "user", "content": user_query})

            success, response = self.ollama.generate_chat(
                messages=messages,
                model=model,
                temperature=0.3,
                timeout=40.0,
            )
            if success and response.strip():
                return response.strip()

        # Deterministic Grounded Fallback
        return self._generate_grounded_fallback(project, user_query)

    def _generate_grounded_fallback(self, project: Project, query: str) -> str:
        """Generates grounded responses for common hackathon queries when Ollama is offline."""
        q = query.lower()

        # 1. What should we work on next? / What should each member do?
        if "next" in q or "who" in q or "each" in q:
            lines = ["Here are the immediate recommended next actions for each member:"]
            for m in project.team_members:
                # Find ready tasks for this member
                ready = [
                    t
                    for t in project.tasks
                    if t.assigned_to == m.name
                    and t.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS)
                    and DependencyService.get_task_readiness(t, project.tasks).is_ready
                ]
                if ready:
                    top = ready[0]
                    lines.append(
                        f"• **{m.name}**: Work on **[{top.id}] {top.title}** ({top.estimated_hours}h, Priority: {top.priority.value}). Prerequisite dependencies are fulfilled."
                    )
                else:
                    lines.append(
                        f"• **{m.name}**: No unblocked tasks waiting. Assist teammate with integration testing or pitch preparation."
                    )
            return "\n".join(lines)

        # 2. Which tasks are blocking progress?
        if "blocking" in q or "blocker" in q:
            active_blockers = [b for b in project.blockers if b.status == BlockerStatus.ACTIVE]
            waiting = DependencyService.get_waiting_analysis(project.tasks)
            if not active_blockers and not waiting:
                return "Good news! There are currently no active blockers or dependency bottlenecks in the project."

            lines = ["**Active Blockers & Bottlenecks:**"]
            for b in active_blockers:
                lines.append(f"• **[{b.id}]** ({b.blocker_type}): {b.description}")
            for w in waiting:
                lines.append(
                    f"• Task **[{w['task_id']}] {w['task_title']}** is waiting on: {', '.join(w['waiting_on'])}"
                )
            return "\n".join(lines)

        # 3. What can we finish in the next 2 hours?
        if "2 hours" in q or "two hours" in q or "quick" in q:
            quick_tasks = [
                t
                for t in project.tasks
                if t.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS)
                and t.estimated_hours <= 2.5
                and DependencyService.get_task_readiness(t, project.tasks).is_ready
            ]
            if not quick_tasks:
                return "There are no ready tasks with duration <= 2.5 hours. Consider splitting a larger task or pair-programming to accelerate progress."

            lines = ["Here are the tasks you can complete within the next ~2 hours:"]
            for t in quick_tasks:
                lines.append(
                    f"• **[{t.id}] {t.title}** ({t.estimated_hours}h) — Assigned to {t.assigned_to}"
                )
            return "\n".join(lines)

        # 4. Are we on track to finish before deadline?
        if "on track" in q or "deadline" in q or "schedule" in q:
            remaining_hours = sum(
                t.estimated_hours for t in project.tasks if t.status != TaskStatus.DONE
            )
            completed_hours = sum(
                t.estimated_hours for t in project.tasks if t.status == TaskStatus.DONE
            )
            total = sum(t.estimated_hours for t in project.tasks)
            pct = round((completed_hours / total) * 100, 1) if total > 0 else 0

            status_str = (
                "⚠️ **Behind schedule:** Remaining tasks exceed deadline! Use the **Replanning Agent** to cut scope."
                if remaining_hours > project.deadline_hours
                else "✅ **On track!** Remaining estimated workload fits within your hackathon deadline."
            )

            return f"""{status_str}
• **Completed Work:** {completed_hours:.1f}h ({pct}%)
• **Remaining Work:** {remaining_hours:.1f}h
• **Available Deadline:** {project.deadline_hours:.1f}h
• **Active Blockers:** {sum(1 for b in project.blockers if b.status == BlockerStatus.ACTIVE)}"""

        # 5. Which features should we cut for MVP?
        if "cut" in q or "scope" in q or "drop" in q or "stretch" in q:
            stretch_tasks = [
                t
                for t in project.tasks
                if (not t.is_mvp or t.priority == TaskPriority.LOW)
                and t.status != TaskStatus.DONE
            ]
            blocked_tasks = [t for t in project.tasks if t.status == TaskStatus.BLOCKED]

            lines = ["**Recommended Scope Cuts for Hackathon MVP:**"]
            if stretch_tasks:
                for t in stretch_tasks:
                    lines.append(
                        f"• **[{t.id}] {t.title}** ({t.estimated_hours}h) — Already marked Low Priority/Stretch."
                    )
            if blocked_tasks:
                for t in blocked_tasks:
                    lines.append(
                        f"• **[{t.id}] {t.title}** ({t.estimated_hours}h) — Currently Blocked. Replace with synthetic/mock data to unblock judges demo."
                    )
            if not stretch_tasks and not blocked_tasks:
                lines.append(
                    "All remaining tasks are currently marked High/Medium MVP. Check the **Blockers & Replanning** tab to auto-generate a lean MVP plan."
                )
            return "\n".join(lines)

        # Generic summary
        completed_count = sum(1 for t in project.tasks if t.status == TaskStatus.DONE)
        return (
            f"**Project Summary for {project.name}:**\n"
            f"• Tasks: {completed_count}/{len(project.tasks)} done\n"
            f"• Team: {', '.join([m.name for m in project.team_members])}\n"
            f"• Ask me specific questions like: 'What should we work on next?', 'Which tasks are blocking us?', or 'Are we on track?'"
        )
