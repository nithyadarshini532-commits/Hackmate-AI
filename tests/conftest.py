"""Pytest configuration and shared fixtures for HackMate AI."""
import os
import sys
import tempfile
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from models.schemas import Project, Task, TaskPriority, TaskStatus, TeamMember
from services.storage_service import StorageService
from services.project_service import ProjectService


@pytest.fixture
def temp_db_path():
    """Provides a temporary SQLite database path for isolated testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


@pytest.fixture
def storage(temp_db_path):
    """StorageService pointing to temp database."""
    return StorageService(db_path=temp_db_path)


@pytest.fixture
def project_service(storage):
    """ProjectService initialized with temp storage."""
    return ProjectService(storage=storage)


@pytest.fixture
def sample_members():
    return [
        TeamMember(
            id="m1",
            name="Alice",
            role="Frontend & UI",
            skills=["Streamlit", "UI/UX", "Python", "CSS"],
            max_hours=24.0,
        ),
        TeamMember(
            id="m2",
            name="Bob",
            role="Backend & AI",
            skills=["FastAPI", "Ollama", "Python", "SQLite"],
            max_hours=24.0,
        ),
    ]


@pytest.fixture
def sample_project(project_service, sample_members):
    tasks = [
        Task(
            id="TASK-1",
            title="Setup DB",
            priority=TaskPriority.HIGH,
            assigned_to="Bob",
            estimated_hours=2.0,
            status=TaskStatus.DONE,
            dependencies=[],
            acceptance_criteria=["DB ready"],
            suggested_order=1,
        ),
        Task(
            id="TASK-2",
            title="Build UI",
            priority=TaskPriority.HIGH,
            assigned_to="Alice",
            estimated_hours=3.0,
            status=TaskStatus.IN_PROGRESS,
            dependencies=["TASK-1"],
            acceptance_criteria=["UI renders"],
            suggested_order=2,
        ),
        Task(
            id="TASK-3",
            title="Connect AI",
            priority=TaskPriority.MEDIUM,
            assigned_to="Bob",
            estimated_hours=4.0,
            status=TaskStatus.TODO,
            dependencies=["TASK-1"],
            acceptance_criteria=["Ollama hooked up"],
            suggested_order=3,
        ),
    ]
    return project_service.create_project(
        name="Test Project",
        idea="Test Idea",
        problem_statement="Test Problem",
        category="AI",
        deadline_hours=24.0,
        team_members=sample_members,
        tasks=tasks,
    )
