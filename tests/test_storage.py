"""Tests for StorageService and ProjectService persistence and operations."""
from models.schemas import BlockerStatus, ProposalStatus, TaskPriority, TaskStatus


def test_project_creation_and_load(project_service, sample_project):
    loaded = project_service.get_project(sample_project.id)
    assert loaded is not None
    assert loaded.name == "Test Project"
    assert len(loaded.tasks) == 3
    assert len(loaded.team_members) == 2


def test_task_status_updates(project_service, sample_project):
    # TASK-2 is In Progress. Mark it Done.
    success, msg = project_service.update_task_status(
        sample_project, "TASK-2", TaskStatus.DONE, author="Alice"
    )
    assert success is True
    # Verify in loaded project from DB
    reloaded = project_service.get_project(sample_project.id)
    t2 = next(t for t in reloaded.tasks if t.id == "TASK-2")
    assert t2.status == TaskStatus.DONE


def test_task_status_blocked_by_dependency(project_service, sample_project):
    # Reset TASK-1 to TODO
    sample_project.tasks[0].status = TaskStatus.TODO
    project_service.storage.save_project(sample_project)

    # Attempt to mark TASK-2 (which depends on TASK-1) as IN_PROGRESS
    success, msg = project_service.update_task_status(
        sample_project, "TASK-2", TaskStatus.IN_PROGRESS, author="Alice"
    )
    assert success is False
    assert "Waiting for" in msg


def test_calculate_metrics(project_service, sample_project):
    metrics = project_service.calculate_metrics(sample_project)
    assert metrics["total_tasks"] == 3
    assert metrics["completed_tasks"] == 1
    # 1/3 = 33.3%
    assert metrics["completion_percentage"] == 33.3
    # TASK-2 (3.0h) + TASK-3 (4.0h) = 7.0h remaining
    assert metrics["remaining_estimated_hours"] == 7.0
    # Workload distribution: Alice has 3.0h, Bob has 4.0h active
    assert metrics["member_workloads"]["Alice"]["active_hours"] == 3.0
    assert metrics["member_workloads"]["Bob"]["active_hours"] == 4.0


def test_blocker_reporting_and_resolution(project_service, sample_project):
    blocker = project_service.report_blocker(
        project=sample_project,
        task_id="TASK-3",
        reported_by="Bob",
        blocker_type="API Failure",
        description="Ollama connection timed out",
    )
    assert blocker.status == BlockerStatus.ACTIVE
    assert sample_project.tasks[2].status == TaskStatus.BLOCKED

    # Resolve blocker
    res = project_service.resolve_blocker(sample_project, blocker.id, author="Bob")
    assert res is True
    assert sample_project.blockers[0].status == BlockerStatus.RESOLVED


def test_replan_proposal_approval_and_rejection(project_service, sample_project):
    from agents.replanner import ReplanningAgent
    from unittest.mock import MagicMock
    from services.ollama_service import OllamaService

    mock_ollama = MagicMock(spec=OllamaService)
    mock_ollama.check_health.return_value = {"connected": False, "models": []}
    replanner = ReplanningAgent(ollama=mock_ollama)
    # Report a blocker on TASK-3
    project_service.report_blocker(
        sample_project,
        task_id="TASK-3",
        reported_by="Bob",
        blocker_type="Library Bug",
        description="Bug in backend",
    )

    # Generate proposal
    proposal = replanner.generate_replan(sample_project)
    sample_project.replan_proposals.append(proposal)
    project_service.storage.save_project(sample_project)

    assert proposal.status == ProposalStatus.PENDING

    # Test Rejection first
    ok_reject, _ = project_service.reject_replan_proposal(sample_project, proposal.id)
    assert ok_reject is True
    assert proposal.status == ProposalStatus.REJECTED

    # Create another proposal and test Acceptance
    proposal2 = replanner.generate_replan(sample_project)
    sample_project.replan_proposals.append(proposal2)
    project_service.storage.save_project(sample_project)

    ok_accept, msg = project_service.apply_replan_proposal(sample_project, proposal2.id)
    assert ok_accept is True
    assert proposal2.status == ProposalStatus.ACCEPTED

    # Verify tasks updated in database
    reloaded = project_service.get_project(sample_project.id)
    assert len(reloaded.tasks) == len(proposal2.revised_tasks)
