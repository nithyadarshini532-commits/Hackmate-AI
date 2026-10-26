"""Pre-seeded realistic hackathon demo data for HackMate AI."""
from datetime import datetime, timedelta
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


def get_demo_project() -> Project:
    """Creates a comprehensive, realistic hackathon demo project."""
    now = datetime.now()

    alex = TeamMember(
        id="M1",
        name="Alex Rivera",
        role="Frontend, Dashboard & Integration",
        skills=["Streamlit", "Python", "UI/UX Design", "Plotly", "API Integration"],
        max_hours=24.0,
        current_workload_hours=12.5,
    )

    sam = TeamMember(
        id="M2",
        name="Sam Chen",
        role="AI Models, Backend & Edge Logic",
        skills=["Python", "Ollama", "Local LLMs", "Signal Processing", "Data Pipelines"],
        max_hours=24.0,
        current_workload_hours=13.5,
    )

    tasks = [
        Task(
            id="TASK-1",
            title="Architecture & Schema Design",
            description="Define JSON payload format for patient vitals, alert thresholds, and triage states.",
            priority=TaskPriority.HIGH,
            assigned_to="Alex Rivera",
            estimated_hours=2.0,
            status=TaskStatus.DONE,
            dependencies=[],
            acceptance_criteria=[
                "Pydantic schema defined for vitals (heart rate, SpO2, blood pressure)",
                "Documented error handling response formats",
            ],
            suggested_order=1,
            notes="Completed on schedule. Shared schema models in repository.",
            is_mvp=True,
        ),
        Task(
            id="TASK-2",
            title="Synthetic Vitals Data Streamer",
            description="Build a realistic generator simulating multi-patient ICU vitals with periodic abnormal spikes.",
            priority=TaskPriority.HIGH,
            assigned_to="Sam Chen",
            estimated_hours=3.0,
            status=TaskStatus.DONE,
            dependencies=["TASK-1"],
            acceptance_criteria=[
                "Generates continuous 1Hz vitals stream for 4 patients",
                "Injects tachycardic and hypoxic episodes on demand",
            ],
            suggested_order=2,
            notes="Working smoothly with configurable noise and anomaly triggers.",
            is_mvp=True,
        ),
        Task(
            id="TASK-3",
            title="Streamlit Real-Time Dashboard Layout",
            description="Design modern dark-mode monitoring interface with vital cards, trend graphs, and triage badges.",
            priority=TaskPriority.HIGH,
            assigned_to="Alex Rivera",
            estimated_hours=4.0,
            status=TaskStatus.DONE,
            dependencies=["TASK-1"],
            acceptance_criteria=[
                "Custom dark aesthetic with cyan and purple telemetry widgets",
                "Auto-refreshing sparklines and urgency color-coding",
            ],
            suggested_order=3,
            notes="UI template validated with sample mockup charts.",
            is_mvp=True,
        ),
        Task(
            id="TASK-4",
            title="BLE Hardware Sensor Integration",
            description="Interface with physical Bluetooth Low Energy pulse oximeter dongle for live biometric streaming.",
            priority=TaskPriority.HIGH,
            assigned_to="Sam Chen",
            estimated_hours=4.5,
            status=TaskStatus.BLOCKED,
            dependencies=["TASK-2"],
            acceptance_criteria=[
                "Pairs via Bluetooth dongle",
                "Streams live BPM and SpO2 to processing thread",
            ],
            suggested_order=4,
            notes="CRITICAL BLOCKER: Bluetooth driver disconnects repeatedly on the Windows test machine. See Blocker BLK-1.",
            is_mvp=True,
        ),
        Task(
            id="TASK-5",
            title="Local Ollama Triage Explanation Agent",
            description="Prompt local Qwen 2.5 3B model to generate bedside nurse summaries explaining detected anomalies.",
            priority=TaskPriority.HIGH,
            assigned_to="Sam Chen",
            estimated_hours=4.0,
            status=TaskStatus.IN_PROGRESS,
            dependencies=["TASK-2"],
            acceptance_criteria=[
                "Returns concise clinical reasoning under 3 seconds",
                "Includes recommended immediate nurse verification step",
            ],
            suggested_order=5,
            notes="Prompt engineered and initial JSON parsing working; tuning latency.",
            is_mvp=True,
        ),
        Task(
            id="TASK-6",
            title="Emergency Triage Patient Queue View",
            description="Interactive bedside priority board allowing doctors to acknowledge alarms and dispatch staff.",
            priority=TaskPriority.MEDIUM,
            assigned_to="Alex Rivera",
            estimated_hours=3.5,
            status=TaskStatus.TODO,
            dependencies=["TASK-3"],
            acceptance_criteria=[
                "Sorts patients dynamically by AI urgency score",
                "One-click status dispatch with visual audit trail",
            ],
            suggested_order=6,
            notes="Ready to start as soon as backend integration hook is verified.",
            is_mvp=True,
        ),
        Task(
            id="TASK-7",
            title="End-to-End System Integration & Testing",
            description="Wire Streamlit frontend to local Ollama agent and vitals streaming backend with end-to-end pytest suite.",
            priority=TaskPriority.HIGH,
            assigned_to="Alex Rivera",
            estimated_hours=3.0,
            status=TaskStatus.TODO,
            dependencies=["TASK-4", "TASK-5", "TASK-6"],
            acceptance_criteria=[
                "Seamless pipeline without UI freezes",
                "Full automated test coverage with passing pytest suite",
            ],
            suggested_order=7,
            notes="Currently blocked because TASK-4 is blocked.",
            is_mvp=True,
        ),
        Task(
            id="TASK-8",
            title="Pitch Deck & Final Demo Walkthrough",
            description="Prepare 3-minute hackathon pitch slides and live demonstration walkthrough video script.",
            priority=TaskPriority.MEDIUM,
            assigned_to="Sam Chen",
            estimated_hours=2.0,
            status=TaskStatus.TODO,
            dependencies=["TASK-7"],
            acceptance_criteria=[
                "Slide deck covering problem, architecture, agentic workflow, and impact",
                "Dry run completed under 3 minutes",
            ],
            suggested_order=8,
            notes="Scheduled for final 3 hours before hackathon submission.",
            is_mvp=False,
        ),
    ]

    blockers = [
        Blocker(
            id="BLK-1",
            task_id="TASK-4",
            reported_by="Sam Chen",
            blocker_type="API/Library Failure",
            description="Bluetooth Low Energy sensor library ('bleak') is throwing device enumeration timeout on Windows. Physical BLE hardware connection is unstable.",
            is_inferred=False,
            status=BlockerStatus.ACTIVE,
            resolution_steps=[
                "Descope physical BLE hardware from MVP to avoid missing hackathon deadline.",
                "Rely on the verified Synthetic Vitals Streamer (TASK-2) for live demo presentation.",
                "Remove TASK-4 as a prerequisite for TASK-7 (End-to-End Integration).",
                "Record a short backup video showing physical sensor demo separately if needed.",
            ],
            created_at=(now - timedelta(hours=2)).isoformat(),
        )
    ]

    # Pre-calculated demo replan proposal
    revised_tasks = [
        # Keep 1, 2, 3 as Done
        tasks[0],
        tasks[1],
        tasks[2],
        # Deprioritize TASK-4 from MVP and unblock downstream
        Task(
            id="TASK-4",
            title="BLE Hardware Sensor Integration (Descoped to Stretch Goal)",
            description="Optional stretch goal: connect physical BLE pulse oximeter if time permits after MVP.",
            priority=TaskPriority.LOW,
            assigned_to="Sam Chen",
            estimated_hours=1.5,
            status=TaskStatus.BLOCKED,
            dependencies=["TASK-2"],
            acceptance_criteria=["Live BLE telemetry if dongle works"],
            suggested_order=8,
            notes="Descoped by Replanning Agent: downstream tasks no longer wait on this.",
            is_mvp=False,
        ),
        tasks[4],  # TASK-5 (Ollama)
        tasks[5],  # TASK-6 (Queue View)
        # TASK-7 now only depends on TASK-5 and TASK-6 (TASK-4 unlinked!)
        Task(
            id="TASK-7",
            title="End-to-End System Integration & Testing (Unblocked)",
            description="Wire Streamlit frontend to local Ollama agent and synthetic vitals streamer.",
            priority=TaskPriority.HIGH,
            assigned_to="Alex Rivera",
            estimated_hours=3.0,
            status=TaskStatus.TODO,
            dependencies=["TASK-5", "TASK-6"],  # TASK-4 removed!
            acceptance_criteria=[
                "Passes all pytest unit tests",
                "Realtime alerts display properly in UI",
            ],
            suggested_order=7,
            notes="Prerequisite TASK-4 unlinked by Replanning Agent.",
            is_mvp=True,
        ),
        tasks[7],  # TASK-8 (Pitch Deck)
    ]

    demo_proposal = ReplanProposal(
        id="PROP-DEMO",
        project_id="demo-healthpulse",
        summary="[Demo Replan] Descope flaky BLE hardware driver from MVP critical path to unblock final integration and testing.",
        previous_tasks=tasks,
        revised_tasks=revised_tasks,
        recommended_changes=[
            "Descope TASK-4 (BLE Hardware Sensor) from MVP critical path and convert to post-MVP stretch goal.",
            "Remove TASK-4 dependency from TASK-7 (Integration), immediately unblocking system integration testing.",
            "Reassign Sam Chen's available hours towards polishing TASK-5 (Local Ollama Triage Agent) and prompt latency.",
            "Maintain Alex Rivera on UI and Integration to guarantee a flawless submission demo.",
        ],
        reasons=[
            "BLE driver timeout cannot be reliably fixed within the remaining 8 hours of the hackathon.",
            "Synthetic Streamer (TASK-2) is already verified and produces identical vitals telemetry for judges.",
            "Hardware sensor failure is a high-risk liability during live judge presentation.",
        ],
        risks_and_tradeoffs=[
            "Trade-off: Judges will see synthetic ICU telemetry rather than live fingertip pulse sensor.",
            "Benefit: Eliminates crash risk during live demo and guarantees complete end-to-end testing.",
        ],
        member_next_actions={
            "Alex Rivera": "Finalize TASK-6 (Emergency Triage Queue) and prepare integration harness for TASK-7.",
            "Sam Chen": "Focus 100% on TASK-5 (Ollama response formatting & latency) to ensure instant triage feedback.",
        },
        status=ProposalStatus.PENDING,
        created_at=(now - timedelta(minutes=45)).isoformat(),
    )

    activity_logs = [
        ActivityLog(
            id="LOG-1",
            timestamp=(now - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S"),
            action_type="PLAN_CREATED",
            description="Project initialized: HealthPulse AI with 8 structured tasks assigned across 2 team members.",
            author="Planner Agent",
        ),
        ActivityLog(
            id="LOG-2",
            timestamp=(now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
            action_type="TASK_STATUS_UPDATED",
            description="Alex Rivera marked TASK-1 (Architecture & Schema Design) as DONE.",
            author="Alex Rivera",
        ),
        ActivityLog(
            id="LOG-3",
            timestamp=(now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
            action_type="TASK_STATUS_UPDATED",
            description="Sam Chen marked TASK-2 (Synthetic Vitals Data Streamer) as DONE.",
            author="Sam Chen",
        ),
        ActivityLog(
            id="LOG-4",
            timestamp=(now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
            action_type="TASK_STATUS_UPDATED",
            description="Alex Rivera marked TASK-3 (Streamlit Real-Time Dashboard Layout) as DONE.",
            author="Alex Rivera",
        ),
        ActivityLog(
            id="LOG-5",
            timestamp=(now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            action_type="BLOCKER_REPORTED",
            description="Sam Chen reported Blocker BLK-1 on TASK-4 (Bluetooth sensor driver timeout).",
            author="Sam Chen",
        ),
        ActivityLog(
            id="LOG-6",
            timestamp=(now - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S"),
            action_type="REPLAN_PROPOSED",
            description="AI Replanning Agent generated proposal PROP-DEMO to descope BLE hardware and unblock TASK-7.",
            author="Replanning Agent",
        ),
    ]

    return Project(
        id="demo-healthpulse",
        name="HealthPulse AI",
        idea="Real-time Patient Vitals & Triage Alert System for Emergency Rooms using edge AI and wearable sensor streaming.",
        problem_statement="Emergency room nurses are overwhelmed with sporadic manual charting of vital signs. Critical patient deterioration is often caught too late, leading to preventable clinical complications.",
        category="Healthcare & Edge AI",
        deadline_hours=24.0,
        team_size=2,
        team_members=[alex, sam],
        tasks=tasks,
        blockers=blockers,
        replan_proposals=[demo_proposal],
        activity_logs=activity_logs,
        created_at=(now - timedelta(hours=8)).isoformat(),
        updated_at=now.isoformat(),
    )
