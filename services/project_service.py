"""Project service: high-level business logic, metrics, and state management."""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import uuid

from models.schemas import (
    ActivityLog,
    Blocker,
    BlockerStatus,
    Project,
    ProposalStatus,
    ReplanProposal,
    Task,
    TaskPriority,
    TaskStatus,
    TeamMember,
)
from services.dependency_service import DependencyService
from services.storage_service import StorageService
from data.demo_data import get_demo_project


class ProjectService:
    def __init__(self, storage: Optional[StorageService] = None):
        self.storage = storage or StorageService()

    def create_project(
        self,
        name: str,
        idea: str,
        problem_statement: str,
        category: str,
        deadline_hours: float,
        team_members: List[TeamMember],
        tasks: Optional[List[Task]] = None,
    ) -> Project:
        """Creates and persists a new project."""
        project_id = f"proj-{uuid.uuid4().hex[:8]}"
        now_str = datetime.now().isoformat()
        initial_tasks = tasks or []

        log = ActivityLog(
            id=f"log-{uuid.uuid4().hex[:6]}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action_type="PLAN_CREATED",
            description=f"Created project '{name}' with {len(initial_tasks)} tasks.",
            author="System",
        )

        project = Project(
            id=project_id,
            name=name.strip(),
            idea=idea.strip(),
            problem_statement=problem_statement.strip(),
            category=category.strip(),
            deadline_hours=deadline_hours,
            team_size=len(team_members),
            team_members=team_members,
            tasks=initial_tasks,
            blockers=[],
            replan_proposals=[],
            activity_logs=[log],
            created_at=now_str,
            updated_at=now_str,
        )

        self._recalculate_member_workloads(project)
        self.storage.save_project(project)
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.storage.get_project(project_id)

    def list_projects(self) -> List[Dict[str, str]]:
        return self.storage.list_projects()

    def load_demo(self) -> Project:
        """Loads and persists the pre-seeded hackathon demo project."""
        demo = get_demo_project()
        self.storage.save_project(demo)
        return demo

    def _recalculate_member_workloads(self, project: Project) -> None:
        """Updates each team member's active workload hours based on current tasks."""
        workload_map: Dict[str, float] = {m.name: 0.0 for m in project.team_members}
        for task in project.tasks:
            if task.status != TaskStatus.DONE and task.assigned_to in workload_map:
                workload_map[task.assigned_to] += task.estimated_hours

        for m in project.team_members:
            m.current_workload_hours = round(workload_map.get(m.name, 0.0), 1)

    def update_task_status(
        self,
        project: Project,
        task_id: str,
        new_status: TaskStatus,
        author: str = "User",
        notes: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Updates task status after validating prerequisite dependencies if moving to In Progress or Done."""
        target_task = next((t for t in project.tasks if t.id.upper() == task_id.upper()), None)
        if not target_task:
            return False, f"Task {task_id} not found."

        # If user is attempting to mark In Progress or Done, verify dependencies
        if new_status in (TaskStatus.IN_PROGRESS, TaskStatus.DONE):
            readiness = DependencyService.get_task_readiness(target_task, project.tasks)
            if not readiness.is_ready and target_task.status != TaskStatus.DONE:
                return (
                    False,
                    f"Cannot move task '{target_task.title}' to {new_status.value}. {readiness.reason}",
                )

        old_status = target_task.status
        target_task.status = new_status
        if notes is not None:
            target_task.notes = notes.strip()

        # Check if any associated blocker should be marked resolved if task is marked Done
        if new_status == TaskStatus.DONE:
            for b in project.blockers:
                if b.task_id and b.task_id.upper() == task_id.upper() and b.status == BlockerStatus.ACTIVE:
                    b.status = BlockerStatus.RESOLVED
                    b.resolved_at = datetime.now().isoformat()

        # Log activity
        log = ActivityLog(
            id=f"log-{uuid.uuid4().hex[:6]}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action_type="TASK_UPDATED",
            description=f"{author} changed status of [{target_task.id}] '{target_task.title}' from {old_status.value} to {new_status.value}.",
            author=author,
        )
        project.activity_logs.insert(0, log)
        project.updated_at = datetime.now().isoformat()

        self._recalculate_member_workloads(project)
        self.storage.save_project(project)
        return True, f"Status updated to {new_status.value}."

    def update_task_details(
        self,
        project: Project,
        task_id: str,
        title: str,
        assigned_to: str,
        priority: TaskPriority,
        estimated_hours: float,
        notes: str,
        dependencies: List[str],
        author: str = "User",
    ) -> Tuple[bool, str]:
        """Edits task parameters with cycle detection validation."""
        target_task = next((t for t in project.tasks if t.id.upper() == task_id.upper()), None)
        if not target_task:
            return False, f"Task {task_id} not found."

        # Tentatively update dependencies to test for circular dependency
        old_deps = target_task.dependencies
        target_task.dependencies = dependencies
        validation = DependencyService.validate_dependencies(project.tasks)
        if not validation.is_valid:
            target_task.dependencies = old_deps
            return False, f"Dependency validation failed: {'; '.join(validation.error_messages)}"

        target_task.title = title
        target_task.assigned_to = assigned_to
        target_task.priority = priority
        target_task.estimated_hours = estimated_hours
        target_task.notes = notes

        log = ActivityLog(
            id=f"log-{uuid.uuid4().hex[:6]}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action_type="TASK_UPDATED",
            description=f"{author} updated details for task [{target_task.id}].",
            author=author,
        )
        project.activity_logs.insert(0, log)
        project.updated_at = datetime.now().isoformat()

        self._recalculate_member_workloads(project)
        self.storage.save_project(project)
        return True, "Task updated successfully."

    def report_blocker(
        self,
        project: Project,
        task_id: Optional[str],
        reported_by: str,
        blocker_type: str,
        description: str,
        is_inferred: bool = False,
        resolution_steps: Optional[List[str]] = None,
    ) -> Blocker:
        """Reports a new blocker. If task_id provided, sets that task to Blocked."""
        blocker_id = f"BLK-{len(project.blockers) + 1}"
        blocker = Blocker(
            id=blocker_id,
            task_id=task_id,
            reported_by=reported_by,
            blocker_type=blocker_type,
            description=description,
            is_inferred=is_inferred,
            status=BlockerStatus.ACTIVE,
            resolution_steps=resolution_steps or [],
            created_at=datetime.now().isoformat(),
        )
        project.blockers.insert(0, blocker)

        if task_id:
            for t in project.tasks:
                if t.id.upper() == task_id.upper() and t.status != TaskStatus.DONE:
                    t.status = TaskStatus.BLOCKED

        prefix = "[Automated Risk]" if is_inferred else "[Reported Blocker]"
        log = ActivityLog(
            id=f"log-{uuid.uuid4().hex[:6]}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action_type="BLOCKER_REPORTED",
            description=f"{prefix} {reported_by} reported: {description[:80]}...",
            author=reported_by,
        )
        project.activity_logs.insert(0, log)
        project.updated_at = datetime.now().isoformat()

        self._recalculate_member_workloads(project)
        self.storage.save_project(project)
        return blocker

    def resolve_blocker(self, project: Project, blocker_id: str, author: str = "User") -> bool:
        """Resolves an active blocker."""
        target = next((b for b in project.blockers if b.id == blocker_id), None)
        if not target:
            return False

        target.status = BlockerStatus.RESOLVED
        target.resolved_at = datetime.now().isoformat()

        # If task was marked Blocked, restore it to To Do or In Progress if dependencies met
        if target.task_id:
            for t in project.tasks:
                if t.id.upper() == target.task_id.upper() and t.status == TaskStatus.BLOCKED:
                    readiness = DependencyService.get_task_readiness(t, project.tasks)
                    t.status = TaskStatus.TODO if readiness.is_ready else TaskStatus.BLOCKED

        log = ActivityLog(
            id=f"log-{uuid.uuid4().hex[:6]}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action_type="BLOCKER_RESOLVED",
            description=f"{author} resolved blocker [{target.id}].",
            author=author,
        )
        project.activity_logs.insert(0, log)
        project.updated_at = datetime.now().isoformat()

        self._recalculate_member_workloads(project)
        self.storage.save_project(project)
        return True

    def apply_replan_proposal(
        self, project: Project, proposal_id: str, author: str = "User"
    ) -> Tuple[bool, str]:
        """Applies an approved replan proposal to the project."""
        proposal = next((p for p in project.replan_proposals if p.id == proposal_id), None)
        if not proposal:
            return False, "Proposal not found."

        if proposal.status != ProposalStatus.PENDING:
            return False, f"Proposal is already {proposal.status.value}."

        # Validate proposed tasks
        validation = DependencyService.validate_dependencies(proposal.revised_tasks)
        if not validation.is_valid:
            return False, f"Proposed plan has dependency errors: {'; '.join(validation.error_messages)}"

        # Replace project tasks with revised tasks
        project.tasks = proposal.revised_tasks
        proposal.status = ProposalStatus.ACCEPTED

        log = ActivityLog(
            id=f"log-{uuid.uuid4().hex[:6]}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action_type="REPLAN_ACCEPTED",
            description=f"{author} approved Replan Proposal [{proposal.id}]: {proposal.summary}",
            author=author,
        )
        project.activity_logs.insert(0, log)
        project.updated_at = datetime.now().isoformat()

        self._recalculate_member_workloads(project)
        self.storage.save_project(project)
        return True, "Replan proposal successfully applied to project!"

    def reject_replan_proposal(
        self, project: Project, proposal_id: str, author: str = "User"
    ) -> Tuple[bool, str]:
        """Rejects a replan proposal without altering tasks."""
        proposal = next((p for p in project.replan_proposals if p.id == proposal_id), None)
        if not proposal:
            return False, "Proposal not found."

        if proposal.status != ProposalStatus.PENDING:
            return False, f"Proposal is already {proposal.status.value}."

        proposal.status = ProposalStatus.REJECTED
        log = ActivityLog(
            id=f"log-{uuid.uuid4().hex[:6]}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action_type="REPLAN_REJECTED",
            description=f"{author} rejected Replan Proposal [{proposal.id}]. Existing plan maintained.",
            author=author,
        )
        project.activity_logs.insert(0, log)
        project.updated_at = datetime.now().isoformat()

        self.storage.save_project(project)
        return True, "Replan proposal rejected. Current plan kept."

    def calculate_metrics(self, project: Project) -> Dict[str, Any]:
        """Calculates real-time project metrics."""
        total = len(project.tasks)
        completed = sum(1 for t in project.tasks if t.status == TaskStatus.DONE)
        in_progress = sum(1 for t in project.tasks if t.status == TaskStatus.IN_PROGRESS)
        blocked = sum(1 for t in project.tasks if t.status == TaskStatus.BLOCKED)
        todo = sum(1 for t in project.tasks if t.status == TaskStatus.TODO)

        completion_pct = round((completed / total) * 100, 1) if total > 0 else 0.0

        remaining_hours = round(
            sum(t.estimated_hours for t in project.tasks if t.status != TaskStatus.DONE), 1
        )
        total_hours = round(sum(t.estimated_hours for t in project.tasks), 1)

        # Workload per member
        member_workloads: Dict[str, Dict[str, Any]] = {}
        for m in project.team_members:
            assigned_tasks = [t for t in project.tasks if t.assigned_to == m.name]
            active_tasks = [t for t in assigned_tasks if t.status != TaskStatus.DONE]
            done_tasks = [t for t in assigned_tasks if t.status == TaskStatus.DONE]

            active_hours = sum(t.estimated_hours for t in active_tasks)
            done_hours = sum(t.estimated_hours for t in done_tasks)

            member_workloads[m.name] = {
                "role": m.role,
                "skills": m.skills,
                "max_hours": m.max_hours,
                "active_hours": round(active_hours, 1),
                "done_hours": round(done_hours, 1),
                "total_hours": round(active_hours + done_hours, 1),
                "active_count": len(active_tasks),
                "done_count": len(done_tasks),
                "total_count": len(assigned_tasks),
            }

        # Ready vs Waiting tasks
        ready_tasks = [
            t
            for t in project.tasks
            if t.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS)
            and DependencyService.get_task_readiness(t, project.tasks).is_ready
        ]
        waiting_tasks = DependencyService.get_waiting_analysis(project.tasks)

        active_blockers_count = sum(1 for b in project.blockers if b.status == BlockerStatus.ACTIVE)

        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "in_progress_tasks": in_progress,
            "blocked_tasks": blocked,
            "todo_tasks": todo,
            "completion_percentage": completion_pct,
            "remaining_estimated_hours": remaining_hours,
            "total_estimated_hours": total_hours,
            "member_workloads": member_workloads,
            "ready_tasks": ready_tasks,
            "waiting_tasks": waiting_tasks,
            "active_blockers_count": active_blockers_count,
            "is_overdue": remaining_hours > (project.deadline_hours * 1.1),
        }
