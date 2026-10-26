"""Blocker Detection Agent: distinguishes reported blockers from inferred risks and suggests mitigations."""
import logging
from typing import Dict, List, Optional
from models.schemas import Blocker, BlockerStatus, Project, TaskStatus
from services.dependency_service import DependencyService
from services.ollama_service import OllamaService

logger = logging.getLogger(__name__)


class BlockerDetectorAgent:
    def __init__(self, ollama: Optional[OllamaService] = None):
        self.ollama = ollama or OllamaService()

    @staticmethod
    def detect_inferred_risks(project: Project) -> List[Blocker]:
        """Scans project state for implicit risks and bottlenecks.

        CRITICAL: All generated blockers have is_inferred=True so they are
        never falsely presented as user-reported issues.
        """
        risks: List[Blocker] = []
        task_lookup = {t.id.upper(): t for t in project.tasks}

        # 1. Dependency Bottleneck: non-done task with >= 2 dependents
        dependent_counts: Dict[str, int] = {t.id.upper(): 0 for t in project.tasks}
        for t in project.tasks:
            for dep in t.dependencies:
                dep_norm = dep.upper()
                if dep_norm in dependent_counts:
                    dependent_counts[dep_norm] += 1

        for tid, count in dependent_counts.items():
            parent_task = task_lookup.get(tid)
            if parent_task and parent_task.status != TaskStatus.DONE and count >= 2:
                risks.append(
                    Blocker(
                        id=f"RISK-BOTTLENECK-{tid}",
                        task_id=tid,
                        reported_by="Agentic Risk Monitor (Inferred)",
                        blocker_type="Dependency Bottleneck",
                        description=f"Task [{tid}] '{parent_task.title}' has {count} downstream tasks waiting on it. A delay here stalls multiple streams.",
                        is_inferred=True,
                        status=BlockerStatus.ACTIVE,
                        resolution_steps=[
                            f"Prioritize finishing [{tid}] immediately to unblock downstream dependencies.",
                            "Consider having both team members pair program on this task.",
                            "Check if downstream tasks can mock intermediate contracts to start in parallel.",
                        ],
                    )
                )

        # 2. Workload Imbalance: one member has > 70% of active hours
        active_hours_per_member: Dict[str, float] = {m.name: 0.0 for m in project.team_members}
        total_active_hours = 0.0
        for t in project.tasks:
            if t.status != TaskStatus.DONE and t.assigned_to in active_hours_per_member:
                active_hours_per_member[t.assigned_to] += t.estimated_hours
                total_active_hours += t.estimated_hours

        if total_active_hours > 4.0 and len(project.team_members) > 1:
            for name, hrs in active_hours_per_member.items():
                pct = (hrs / total_active_hours) * 100
                if pct > 70.0:
                    other_members = [m for m in project.team_members if m.name != name]
                    other_name = other_members[0].name if other_members else "team member"
                    risks.append(
                        Blocker(
                            id="RISK-WORKLOAD-IMBALANCE",
                            task_id=None,
                            reported_by="Agentic Risk Monitor (Inferred)",
                            blocker_type="Workload Imbalance",
                            description=f"{name} carries {pct:.0f}% ({hrs:.1f}h) of remaining project hours, risking burnout and bottleneck.",
                            is_inferred=True,
                            status=BlockerStatus.ACTIVE,
                            resolution_steps=[
                                f"Reassign 1 or 2 modular tasks from {name} to {other_name}.",
                                "Trigger the AI Replanning Agent to rebalance task allocation.",
                            ],
                        )
                    )

        # 3. Deadline Slippage: remaining hours exceed available hackathon hours
        if total_active_hours > project.deadline_hours:
            risks.append(
                Blocker(
                    id="RISK-TIMELINE-OVERRUN",
                    task_id=None,
                    reported_by="Agentic Risk Monitor (Inferred)",
                    blocker_type="Deadline Slippage",
                    description=f"Total remaining work ({total_active_hours:.1f}h) exceeds remaining hackathon time ({project.deadline_hours:.1f}h).",
                    is_inferred=True,
                    status=BlockerStatus.ACTIVE,
                    resolution_steps=[
                        "Activate AI Replanning Agent to descope non-essential stretch features.",
                        "Mark optional tasks as Low priority and focus purely on the core MVP flow.",
                        "Replace complex custom integrations with pre-built mock data generators.",
                    ],
                )
            )

        return risks

    def suggest_blocker_resolution(
        self, blocker_description: str, blocker_type: str, related_task_title: Optional[str] = None
    ) -> List[str]:
        """Provides context-aware resolution advice for a blocker using Ollama with deterministic fallback."""
        # Deterministic recommendations based on common hackathon blocker types
        b_type_lower = blocker_type.lower()
        if "api" in b_type_lower or "library" in b_type_lower:
            return [
                "Implement a deterministic synthetic/mock data generator so the UI and rest of the app can proceed.",
                "Verify API keys, local ports, and cross-origin resource sharing (CORS) settings.",
                "Descope the broken external API to a stretch goal and focus presentation on working components.",
            ]
        elif "unavailable" in b_type_lower or "member" in b_type_lower:
            return [
                "Trigger Replanning Agent to immediately redistribute incomplete critical tasks to the active member.",
                "Pause non-essential stretch goals and protect the core MVP user flow.",
                "Document completed components so the active member can integrate without friction.",
            ]
        elif "delayed" in b_type_lower or "longer" in b_type_lower:
            return [
                "Timebox the delayed task: stop debugging in 30 minutes if no breakthrough occurs.",
                "Split the task: commit whatever is currently working as a baseline and defer remaining polish.",
                "Consult the AI Project Assistant for alternative lightweight libraries.",
            ]
        elif "integration" in b_type_lower:
            return [
                "Test components in isolation using standalone Python test scripts (pytest).",
                "Log request and response payloads to catch schema mismatches.",
                "Use a simplified JSON bridge rather than complex async streams.",
            ]

        # Default practical hackathon advice
        return [
            "Evaluate whether this task is strictly required for the 3-minute hackathon demo.",
            "Descope edge cases and focus on the 'golden path' demonstration.",
            "Trigger the AI Replanning Agent to calculate an updated schedule.",
        ]
