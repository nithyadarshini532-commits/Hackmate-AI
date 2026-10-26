"""Tests for data model validations and Pydantic schemas."""
import pytest
from pydantic import ValidationError
from models.schemas import (
    Blocker,
    BlockerStatus,
    Project,
    Task,
    TaskPriority,
    TaskStatus,
    TeamMember,
)


def test_team_member_schema():
    member = TeamMember(
        id="m1",
        name="Alex",
        role="Frontend",
        skills=["Python", "Streamlit"],
        max_hours=24.0,
    )
    assert member.name == "Alex"
    assert member.current_workload_hours == 0.0


def test_task_schema_normalization():
    task = Task(
        id="task-10 ",
        title="Valid Title",
        priority=TaskPriority.HIGH,
        estimated_hours=3.5,
        status=TaskStatus.TODO,
    )
    # Check ID normalization to uppercase stripped
    assert task.id == "TASK-10"
    assert task.estimated_hours == 3.5
    assert task.is_mvp is True


def test_task_invalid_hours():
    with pytest.raises(ValidationError):
        Task(
            id="TASK-1",
            title="Invalid",
            estimated_hours=0.0,  # ge=0.1
        )


def test_blocker_schema_inferred_vs_reported():
    # User reported blocker
    user_b = Blocker(
        id="BLK-1",
        task_id="TASK-4",
        reported_by="Sam",
        blocker_type="API/Library Failure",
        description="BLE device timeout",
        is_inferred=False,
    )
    assert user_b.is_inferred is False
    assert user_b.status == BlockerStatus.ACTIVE

    # Inferred risk
    inferred_b = Blocker(
        id="RISK-1",
        task_id="TASK-2",
        reported_by="Risk Monitor",
        blocker_type="Dependency Bottleneck",
        description="Downstream blocker",
        is_inferred=True,
    )
    assert inferred_b.is_inferred is True
