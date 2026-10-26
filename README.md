# ⚡ HackMate AI

**Plan smarter. Build together. Adapt faster.**

HackMate AI is an Agentic AI Project Manager built specifically for 2-person hackathon teams, student builders, and sprint developers. It converts a raw hackathon concept into an actionable, dependency-validated Minimum Viable Product (MVP) plan, balances tasks based on member skillsets, detects bottlenecks and blockers, and dynamically proposes revised schedules when unexpected hurdles arise—all without overwriting the team's plan without explicit approval.

---

## 🌟 Key Capabilities

- **🤖 AI Project Planner (Feature A):** Takes a project idea, category, deadline duration, and 2-member skills/roles to generate a realistic, sequential task plan with time estimates, prerequisite dependencies, acceptance criteria, and MVP tags. Powered by local Ollama (`qwen2.5:3b`) with an intelligent deterministic fallback engine.
- **👥 Smart Task Assignment (Feature B):** Balances workloads between frontend/UI and backend/AI roles using skill-affinity heuristics and capacity constraints. Provides clear rationale for every assignment while allowing manual overrides.
- **📊 Interactive Dashboard (Feature C):** Displays milestone completion %, remaining estimated hours, active vs completed tasks, member capacity meters, and upcoming vs overdue deadlines. All updates persist in SQLite.
- **🔗 Dependency Management & Graph Validation (Feature D):** Pure Python graph engine that detects circular dependencies (DFS cycle detection), flags missing task IDs, evaluates execution readiness, and explains exactly which prerequisites must finish first.
- **🚨 Blocker Detection Agent (Feature E):** Allows members to report blockers (hardware failures, broken libraries, delayed tasks, API errors) with automated mitigation advice. Distinguishes actual reported blockers from system-inferred risks (timeline overrun, single-member overload, dependency bottlenecks).
- **🔄 AI Replanning Agent (Feature F):** Formulates revised golden paths when blockers strike. Descoping stretch goals, unlinking blocked prerequisites with mock data contracts, reassigning tasks, and providing side-by-side plan diffs, reasons, and risks. Staged for team approval before anything is modified.
- **🤝 Team Workspace & Collaboration (Feature G):** Single-machine local collaboration hub with member profiles, capacity tracking, team notes, and live activity history.
- **💬 Project-Aware AI Assistant (Feature H):** Context-grounded chat assistant answering: *"What should we work on next?"*, *"Which tasks are blocking progress?"*, *"What can we finish in 2 hours?"*, and *"Which features should we cut for MVP?"*.
- **🚀 One-Click Demo Mode (Section 7):** Pre-seeded realistic project (*HealthPulse AI*) with 8 tasks, a Bluetooth hardware blocker, and a pre-staged replan proposal so judges can explore the complete workflow immediately, even without Ollama running.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Frontend UI** | Streamlit 1.35+ (Dark Navy aesthetic with Cyan `#00F0FF` and Purple `#8B5CF6` accents) |
| **Backend & Agents** | Python 3.11+ |
| **Local AI Engine** | Ollama Local HTTP API (`http://localhost:11434`) |
| **Default Model** | `qwen2.5:3b` (also supports `llama3.1:8b` or any installed Ollama model) |
| **Data Storage** | SQLite (`data/hackmate.db`) with atomic transactions |
| **Validation** | Pydantic v2 schemas |
| **Testing** | pytest |

---

## 🚀 Quick Start Guide (Windows)

### 1. Prerequisites
- **Python 3.10+** installed on Windows.
- **Ollama** installed on Windows ([Download Ollama for Windows](https://ollama.com/download/windows)).

### 2. Setup Project Directory & Virtual Environment
Open PowerShell or Command Prompt in the project folder:
```powershell
cd C:\Users\Admin\.gemini\antigravity\scratch\hackmate-ai

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
# (If using CMD: .\.venv\Scripts\activate.bat)
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Pull the Local AI Model
Start Ollama if it is not already running, then pull the lightweight `qwen2.5:3b` model:
```powershell
ollama pull qwen2.5:3b
```
*(Optional: HackMate AI also auto-detects existing local models like `llama3.1:8b` via the Settings page!)*

### 5. Launch HackMate AI
```powershell
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### 6. Run Automated Tests
```powershell
pytest -v
```

---

## 🏗️ Architecture & Agent System

```
hackmate-ai/
├── app.py                      # Streamlit application entrypoint & routing
├── requirements.txt            # Python dependencies
├── README.md                   # Complete documentation & demo script
├── .gitignore                  # Git exclusions
├── .env.example                # Configuration template
├── models/
│   ├── __init__.py
│   └── schemas.py              # Pydantic models (Project, Task, Blocker, ReplanProposal, etc.)
├── services/
│   ├── __init__.py
│   ├── storage_service.py      # SQLite persistence layer
│   ├── ollama_service.py       # Ollama HTTP API client & JSON extractor
│   ├── dependency_service.py   # Deterministic graph validator & cycle detector
│   └── project_service.py      # Core business logic & metrics calculations
├── agents/
│   ├── __init__.py
│   ├── planner.py              # Planner Agent (MVP task generation)
│   ├── assignment.py           # Assignment Agent (workload & skill balance)
│   ├── blocker_detector.py     # Blocker & Risk Detection Agent
│   ├── replanner.py            # AI Replanning Agent (diff & proposal staging)
│   └── assistant.py            # Grounded Project Chat Assistant
├── ui/
│   ├── __init__.py
│   ├── styles.py               # Custom CSS (Dark navy, purple & cyan glows)
│   ├── components.py           # Reusable widgets (cards, badges, metrics)
│   ├── overview_page.py        # Overview & executive summary dashboard
│   ├── planner_page.py         # AI Project Planner form & plan review
│   ├── tasks_page.py           # Kanban board & task editor
│   ├── blockers_page.py        # Blocker reporting & Replan Diff Viewer
│   ├── assistant_page.py       # State-grounded AI Chat
│   ├── team_page.py            # Member capacity & notes collaboration
│   └── settings_page.py        # Ollama connection test, model picker, demo loader
├── data/
│   ├── demo_data.py            # Pre-seeded HealthPulse AI project
│   └── hackmate.db             # Local SQLite database
└── tests/
    ├── conftest.py             # Fixtures and test database setup
    ├── test_schemas.py         # Pydantic schema validation tests
    ├── test_dependencies.py    # Cycle detection and dependency tests
    ├── test_storage.py         # SQLite CRUD and persistence tests
    └── test_agents.py          # Unit tests with mocked LLM responses
```

---

## 🎬 3-Minute Judge Demonstration Script (2-Member Team)

Use this step-by-step walkthrough to present HackMate AI to judges:

### Scene 1: Instant Demonstration via Demo Mode (30 seconds)
1. Open the application sidebar and click **🚀 Load Demo Project**.
2. Point out the loaded project: **HealthPulse AI** (Real-time ICU vitals monitoring).
3. Review the **Overview** dashboard:
   - Total tasks (8), Completion rate (37.5%), Remaining hours (12.5h).
   - Team workload split: Alex Rivera (UI & Integration: 6.5h active) vs Sam Chen (AI & Backend: 6.0h active).
   - Point to the active blocker alert in red: **BLK-1** on `TASK-4`.

### Scene 2: Dependency Engine & Blocker Detection (45 seconds)
1. Navigate to the **Tasks** page and view the **📋 Kanban Board**.
2. Show that `TASK-4` (BLE Hardware Sensor) is in the **Blocked** column with red border.
3. Show that `TASK-7` (End-to-End Integration) is waiting in **To Do**:
   - Click on `TASK-7` in the **Edit Task** tab and show the system warning: *"Waiting for 3 prerequisites: TASK-4, TASK-5, TASK-6"*. The system strictly forbids marking it In Progress until prerequisites clear.
4. Navigate to **Blockers & Replanning**:
   - Show the reported blocker: *“Bluetooth Low Energy sensor library ('bleak') timing out on Windows test machine”*.
   - Point out the **Automated Risk Monitor (Inferred)** below, which detected a dependency bottleneck on `TASK-4` without claiming it was reported manually.

### Scene 3: AI Replanning Agent & Staged Approval (60 seconds)
1. In the **Blockers & Replanning** tab, switch to the **⚡ AI Replanning Agent** sub-tab.
2. Review the pre-staged proposal **PROP-DEMO** (or click **Generate Revised Plan with AI**):
   - **Recommended Changes:** Descope `TASK-4` to a post-MVP stretch goal; unlink `TASK-4` from `TASK-7`; switch to the verified Synthetic Streamer (`TASK-2`) for the demo.
   - **Schedule Comparison:** View the side-by-side diff between Current Plan vs Proposed Revised Plan.
   - **Team Next Actions:** Concrete immediate steps assigned to both Alex and Sam.
3. Click **✅ Accept & Apply This Plan to Workspace**.
4. Notice the instant confirmation toast: `TASK-7` is now unlinked from the blocked hardware task!

### Scene 4: Grounded AI Assistant (45 seconds)
1. Navigate to the **AI Assistant** page.
2. Click the preset prompt pill: **👉 What should we work on next?**
3. Notice the agent accurately uses the newly revised project state to advise:
   - Alex should finalize `TASK-6` (Triage Queue View) to prepare for integration.
   - Sam should focus 100% on `TASK-5` (Local Ollama Triage Agent) for instant latency.
4. Click **📅 Are we on track for deadline?** to see exact hour calculations grounded strictly in project data.

---

## 🔧 Troubleshooting & FAQ

| Problem | Cause | Solution |
|---|---|---|
| **Ollama shows "Offline" in sidebar** | Ollama daemon is not running | Open terminal and run `ollama serve` or open Ollama from Start Menu. |
| **Model `qwen2.5:3b` not found** | Model was not pulled locally | Run `ollama pull qwen2.5:3b` in terminal, or select `llama3.1:8b` from Settings if installed. |
| **App runs in Demo Mode** | Ollama is unreachable | The app automatically uses the Smart Heuristic Engine. All features remain 100% functional for judging. |
| **PowerShell script execution disabled** | Windows ExecutionPolicy restriction | Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` in PowerShell. |
| **Streamlit port conflict (8501)** | Another app is using port 8501 | Run `streamlit run app.py --server.port 8502`. |

---

## ⚖️ Implementation Status

- [x] AI Project Planner with structured JSON validation & MVP focus
- [x] Smart Task Assignment balancing skills and workload across 2 members
- [x] Interactive Kanban & List task dashboard with SQLite persistence
- [x] Deterministic Dependency Management with DFS cycle detection
- [x] Blocker Detection distinguishing user reports from inferred risks
- [x] AI Replanning Agent with staged diffs and user approval workflow
- [x] Team Workspace with workload capacity tracking and shared notes
- [x] Context-grounded AI Project Assistant chat
- [x] High-contrast Dark Navy UI with Cyan & Purple glowing accents
- [x] Full automated test suite (22 unit tests passing with pytest)
- [x] Pre-seeded Hackathon Demo Project (*HealthPulse AI*)

---

*HackMate AI — Built for Hackathons. Powered by Local Ollama & Agentic Python.*
