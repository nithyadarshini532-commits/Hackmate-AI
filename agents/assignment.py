"""Assignment Agent: recommends task ownership based on skills, preferences, and workload balance."""
from typing import Dict, List, Optional, Tuple
from models.schemas import Task, TeamMember


class AssignmentAgent:
    @staticmethod
    def _compute_skill_affinity(task: Task, member: TeamMember) -> float:
        """Calculates a matching score between task requirements and member skills/role."""
        score = 0.0
        text_corpus = f"{task.title} {task.description} {' '.join(task.acceptance_criteria)}".lower()

        # Check role match
        role_lower = member.role.lower()
        if "frontend" in role_lower or "ui" in role_lower or "design" in role_lower:
            if any(k in text_corpus for k in ["ui", "dashboard", "frontend", "css", "layout", "view", "component", "screen", "client", "theme", "design"]):
                score += 35.0
        if "backend" in role_lower or "ai" in role_lower or "ml" in role_lower or "data" in role_lower:
            if any(k in text_corpus for k in ["backend", "api", "database", "ai", "model", "llm", "ollama", "pipeline", "service", "algorithm", "endpoint", "server", "data", "processing"]):
                score += 35.0
        if "integration" in role_lower or "testing" in role_lower:
            if any(k in text_corpus for k in ["integration", "test", "pytest", "wire", "e2e", "validation"]):
                score += 25.0

        # Check individual skills
        for skill in member.skills:
            sk_lower = skill.strip().lower()
            if sk_lower and sk_lower in text_corpus:
                score += 20.0

        return score

    @classmethod
    def recommend_assignment(
        cls,
        task: Task,
        team_members: List[TeamMember],
        current_workloads: Dict[str, float],
    ) -> Tuple[str, str]:
        """Returns (recommended_member_name, rationale_string)."""
        if not team_members:
            return "Unassigned", "No team members available."

        if len(team_members) == 1:
            return team_members[0].name, f"Sole team member: assigned to {team_members[0].name}."

        scores: List[Tuple[TeamMember, float, float]] = []  # (member, net_score, affinity)

        for member in team_members:
            affinity = cls._compute_skill_affinity(task, member)
            workload = current_workloads.get(member.name, 0.0)

            # Balancing penalty: -2.5 points per hour of current active workload
            workload_penalty = workload * 2.5
            net_score = affinity - workload_penalty
            scores.append((member, net_score, affinity))

        # Sort by highest net score
        scores.sort(key=lambda x: x[1], reverse=True)
        best_member, best_net, best_affinity = scores[0]

        rationale = (
            f"Assigned to {best_member.name} based on "
            f"{'high skill/role match' if best_affinity > 20 else 'workload availability'} "
            f"(Skill match score: {int(best_affinity)}, active workload: {current_workloads.get(best_member.name, 0.0):.1f}h)."
        )

        return best_member.name, rationale

    @classmethod
    def balance_and_assign_tasks(
        cls, tasks: List[Task], team_members: List[TeamMember]
    ) -> List[Tuple[Task, str]]:
        """Assigns all unassigned or auto-assigned tasks across members with workload tracking.
        Returns list of (Task, rationale).
        """
        if not team_members:
            return [(t, "No members configured.") for t in tasks]

        workload_tracker: Dict[str, float] = {m.name: 0.0 for m in team_members}
        results: List[Tuple[Task, str]] = []

        # Process in suggested_order
        sorted_tasks = sorted(tasks, key=lambda t: t.suggested_order)

        for task in sorted_tasks:
            # If already assigned to an existing member and not 'Unassigned', respect it if requested
            if task.assigned_to and task.assigned_to != "Unassigned":
                member_exists = any(m.name == task.assigned_to for m in team_members)
                if member_exists:
                    workload_tracker[task.assigned_to] += task.estimated_hours
                    results.append((task, f"Maintained existing assignment to {task.assigned_to}."))
                    continue

            best_name, rationale = cls.recommend_assignment(task, team_members, workload_tracker)
            task.assigned_to = best_name
            workload_tracker[best_name] += task.estimated_hours
            results.append((task, rationale))

        return results
