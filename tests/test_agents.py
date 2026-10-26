"""Tests for all Agent implementations with mocks and offline fallback verification."""
from unittest.mock import MagicMock
from models.schemas import TaskPriority, TaskStatus
from agents.planner import PlannerAgent
from agents.assignment import AssignmentAgent
from agents.blocker_detector import BlockerDetectorAgent
from agents.replanner import ReplanningAgent
from agents.assistant import ProjectAssistantAgent
from services.ollama_service import OllamaService


def test_planner_offline_fallback(sample_members):
    # Mock Ollama as offline
    mock_ollama = MagicMock(spec=OllamaService)
    mock_ollama.check_health.return_value = {"connected": False, "models": [], "error": "Offline"}

    planner = PlannerAgent(ollama=mock_ollama)
    tasks, message, is_real_ai = planner.generate_plan(
        name="Offline Plan Project",
        idea="Building an AI edge agent",
        problem_statement="Problem detail",
        category="Agents",
        deadline_hours=24.0,
        team_members=sample_members,
    )
    assert len(tasks) >= 5
    assert is_real_ai is False
    assert "HackMate AI Smart Heuristic Engine" in message
    # Validate no circular dependencies in generated plan
    from services.dependency_service import DependencyService
    val = DependencyService.validate_dependencies(tasks)
    assert val.is_valid is True


def test_planner_llm_json_parsing(sample_members):
    mock_ollama = MagicMock(spec=OllamaService)
    mock_ollama.check_health.return_value = {"connected": True, "models": ["qwen2.5:3b"]}
    mock_ollama.default_model = "qwen2.5:3b"

    sample_json_response = """
    [
      {
        "id": "TASK-1",
        "title": "Design Specs",
        "description": "Schemas and contracts",
        "priority": "High",
        "assigned_to": "Alice",
        "estimated_hours": 2.0,
        "dependencies": [],
        "acceptance_criteria": ["Specs validated"],
        "suggested_order": 1,
        "is_mvp": true
      },
      {
        "id": "TASK-2",
        "title": "Core Logic",
        "description": "Engine",
        "priority": "High",
        "assigned_to": "Bob",
        "estimated_hours": 3.0,
        "dependencies": ["TASK-1"],
        "acceptance_criteria": ["Logic works"],
        "suggested_order": 2,
        "is_mvp": true
      }
    ]
    """
    mock_ollama.generate_chat.return_value = (True, sample_json_response)
    mock_ollama.extract_json.side_effect = OllamaService.extract_json

    planner = PlannerAgent(ollama=mock_ollama)
    tasks, msg, is_real_ai = planner.generate_plan(
        name="Live AI Project",
        idea="Idea",
        problem_statement="",
        category="AI",
        deadline_hours=24.0,
        team_members=sample_members,
    )
    assert is_real_ai is True
    assert len(tasks) == 2
    assert tasks[0].id == "TASK-1"
    assert tasks[1].dependencies == ["TASK-1"]


def test_assignment_agent_workload_balancing(sample_members):
    from models.schemas import Task

    tasks = [
        Task(id="T1", title="Streamlit Frontend View", description="UI design", suggested_order=1),
        Task(id="T2", title="FastAPI Ollama Engine", description="backend AI model", suggested_order=2),
        Task(id="T3", title="CSS Dashboard Styling", description="Frontend visual polish", suggested_order=3),
    ]
    assigned = AssignmentAgent.balance_and_assign_tasks(tasks, sample_members)
    assert len(assigned) == 3

    # Alice has Frontend skills -> should get UI tasks
    assert tasks[0].assigned_to == "Alice"
    # Bob has FastAPI/Ollama -> should get Backend task
    assert tasks[1].assigned_to == "Bob"


def test_blocker_detector_inferred_risks(sample_project):
    detector = BlockerDetectorAgent()
    # Initial project should have bottleneck risk because TASK-1 has 2 dependents (TASK-2 and TASK-3)
    # But TASK-1 is DONE in sample_project, so not a bottleneck.
    # Now set TASK-1 to TODO:
    sample_project.tasks[0].status = TaskStatus.TODO
    risks = detector.detect_inferred_risks(sample_project)
    bottlenecks = [r for r in risks if r.blocker_type == "Dependency Bottleneck"]
    assert len(bottlenecks) == 1
    assert bottlenecks[0].is_inferred is True
    assert bottlenecks[0].task_id == "TASK-1"


def test_assistant_offline_queries(sample_project):
    mock_ollama = MagicMock(spec=OllamaService)
    mock_ollama.check_health.return_value = {"connected": False, "models": []}

    assistant = ProjectAssistantAgent(ollama=mock_ollama)
    # Query: What should we work on next?
    resp1 = assistant.answer_query(sample_project, "What should we work on next?")
    assert "Alice" in resp1 or "Bob" in resp1

    # Query: What can we finish in 2 hours?
    resp2 = assistant.answer_query(sample_project, "What can we finish in the next 2 hours?")
    assert "TASK-" in resp2 or "no ready tasks" in resp2.lower()

    # Query: Are we on track?
    resp3 = assistant.answer_query(sample_project, "Are we on track to finish before deadline?")
    assert "Remaining Work" in resp3
