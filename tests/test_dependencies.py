"""Tests for DependencyService: circular dependency detection, invalid references, and readiness checks."""
from models.schemas import Task, TaskPriority, TaskStatus
from services.dependency_service import DependencyService


def test_acyclic_valid_dependencies():
    tasks = [
        Task(id="TASK-1", title="Task 1", dependencies=[]),
        Task(id="TASK-2", title="Task 2", dependencies=["TASK-1"]),
        Task(id="TASK-3", title="Task 3", dependencies=["TASK-2"]),
    ]
    result = DependencyService.validate_dependencies(tasks)
    assert result.is_valid is True
    assert len(result.cycles) == 0
    assert len(result.invalid_references) == 0


def test_circular_dependency_detection():
    # TASK-1 -> TASK-2 -> TASK-3 -> TASK-1
    tasks = [
        Task(id="TASK-1", title="Task 1", dependencies=["TASK-3"]),
        Task(id="TASK-2", title="Task 2", dependencies=["TASK-1"]),
        Task(id="TASK-3", title="Task 3", dependencies=["TASK-2"]),
    ]
    result = DependencyService.validate_dependencies(tasks)
    assert result.is_valid is False
    assert len(result.cycles) > 0
    assert any("TASK-1" in c for c in result.cycles)


def test_self_dependency_detection():
    tasks = [
        Task(id="TASK-1", title="Task 1", dependencies=["TASK-1"]),
    ]
    result = DependencyService.validate_dependencies(tasks)
    assert result.is_valid is False
    assert any("cannot depend on itself" in err for err in result.error_messages)


def test_invalid_task_reference():
    tasks = [
        Task(id="TASK-1", title="Task 1", dependencies=["TASK-999"]),
    ]
    result = DependencyService.validate_dependencies(tasks)
    assert result.is_valid is False
    assert "TASK-1" in result.invalid_references
    assert "TASK-999" in result.invalid_references["TASK-1"]


def test_task_readiness_logic():
    tasks = [
        Task(id="TASK-1", title="Prereq", status=TaskStatus.TODO),
        Task(id="TASK-2", title="Dependent", status=TaskStatus.TODO, dependencies=["TASK-1"]),
    ]
    # Prereq not done -> Dependent not ready
    readiness = DependencyService.get_task_readiness(tasks[1], tasks)
    assert readiness.is_ready is False
    assert "TASK-1" in readiness.reason

    # Mark Prereq Done -> Dependent becomes ready
    tasks[0].status = TaskStatus.DONE
    readiness_after = DependencyService.get_task_readiness(tasks[1], tasks)
    assert readiness_after.is_ready is True


def test_waiting_analysis():
    tasks = [
        Task(id="TASK-1", title="Backend API", status=TaskStatus.IN_PROGRESS, assigned_to="Bob"),
        Task(id="TASK-2", title="Frontend Client", status=TaskStatus.TODO, assigned_to="Alice", dependencies=["TASK-1"]),
    ]
    analysis = DependencyService.get_waiting_analysis(tasks)
    assert len(analysis) == 1
    assert analysis[0]["task_id"] == "TASK-2"
    assert "Bob on [TASK-1] Backend API" in analysis[0]["what_needs_to_happen"]


def test_topological_sort():
    tasks = [
        Task(id="TASK-3", title="Final", suggested_order=3, dependencies=["TASK-2"]),
        Task(id="TASK-1", title="First", suggested_order=1, dependencies=[]),
        Task(id="TASK-2", title="Middle", suggested_order=2, dependencies=["TASK-1"]),
    ]
    sorted_tasks = DependencyService.get_topological_order(tasks)
    assert [t.id for t in sorted_tasks] == ["TASK-1", "TASK-2", "TASK-3"]
