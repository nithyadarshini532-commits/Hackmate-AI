"""HackMate AI — An Agentic AI Hackathon Project Manager.

Main Streamlit Application Entrypoint.
"""
import sys
import os

# Ensure current folder is in python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import streamlit as st
from services.ollama_service import OllamaService
from services.project_service import ProjectService
from ui.styles import THEME_CSS
from ui.components import render_header
from ui.overview_page import render_overview_page
from ui.planner_page import render_planner_page
from ui.tasks_page import render_tasks_page
from ui.blockers_page import render_blockers_page
from ui.assistant_page import render_assistant_page
from ui.team_page import render_team_page
from ui.settings_page import render_settings_page

# 1. Page Configuration
st.set_page_config(
    page_title="HackMate AI — Agentic Hackathon Project Manager",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Inject Custom Theme CSS
st.markdown(THEME_CSS, unsafe_allow_html=True)

# 3. Initialize Core Services (cached across reruns)
@st.cache_resource
def get_services():
    project_srv = ProjectService()
    ollama_srv = OllamaService()
    return project_srv, ollama_srv


project_service, ollama_service = get_services()

# 4. Session State Initialization
if "selected_model" not in st.session_state:
    # Check if qwen2.5:3b is available, or fallback to first installed
    health = ollama_service.check_health()
    if health["connected"] and "qwen2.5:3b" in health["models"]:
        st.session_state["selected_model"] = "qwen2.5:3b"
    elif health["connected"] and health["models"]:
        st.session_state["selected_model"] = health["models"][0]
    else:
        st.session_state["selected_model"] = "qwen2.5:3b"

# Active project loading
projects_list = project_service.list_projects()
if "active_project_id" not in st.session_state:
    if projects_list:
        st.session_state["active_project_id"] = projects_list[0]["id"]
    else:
        # Load demo project by default on first launch so user has immediate rich experience
        demo = project_service.load_demo()
        st.session_state["active_project_id"] = demo.id
        projects_list = project_service.list_projects()

active_project = (
    project_service.get_project(st.session_state["active_project_id"])
    if st.session_state.get("active_project_id")
    else None
)

# 5. Sidebar Navigation & Project Switcher
with st.sidebar:
    st.markdown('<div class="brand-title">⚡ HackMate AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-tagline">Plan smarter. Build together. Adapt faster.</div>', unsafe_allow_html=True)

    # Project Switcher
    st.markdown("**Active Project:**")
    project_options = {p["id"]: p["name"] for p in projects_list}
    if project_options:
        curr_id = st.session_state.get("active_project_id")
        curr_idx = list(project_options.keys()).index(curr_id) if curr_id in project_options else 0
        selected_pid = st.selectbox(
            "Select Project",
            options=list(project_options.keys()),
            format_func=lambda pid: project_options[pid],
            index=curr_idx,
            label_visibility="collapsed",
        )
        if selected_pid != curr_id:
            st.session_state["active_project_id"] = selected_pid
            st.rerun()
    else:
        st.info("No projects created yet.")

    # Quick Demo Project Button
    if st.button("🚀 Load Demo Project", use_container_width=True):
        demo = project_service.load_demo()
        st.session_state["active_project_id"] = demo.id
        st.session_state["chat_history"] = [
            {
                "role": "assistant",
                "content": f"Loaded demo project **{demo.name}**. I'm tracking all {len(demo.tasks)} tasks, dependencies, and active blocker BLK-1. Ask me anything!",
            }
        ]
        st.success("Demo project activated!")
        st.rerun()

    st.markdown("---")

    # Main Navigation
    nav_selection = st.radio(
        "Navigation",
        [
            "📊 Overview",
            "🤖 Project Planner",
            "📋 Tasks",
            "🚨 Blockers & Replanning",
            "💬 AI Assistant",
            "👥 Team",
            "⚙️ Settings",
        ],
        index=0,
    )

    st.markdown("---")

    # Turbo Mode Toggle
    turbo_mode = st.toggle(
        "⚡ Turbo Mode (Fast & Snappy)",
        value=st.session_state.get("turbo_mode", True),
        help="When enabled, generation runs instantly (<100ms) using deterministic graph & heuristic intelligence. Toggle off for deep local Ollama inference.",
    )
    st.session_state["turbo_mode"] = turbo_mode

    st.markdown("---")

    # Ollama Health Status Badge
    health = ollama_service.check_health()
    active_m = st.session_state.get("selected_model", "qwen2.5:3b")
    if health["connected"]:
        st.markdown(
            f"""
            <div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);border-radius:6px;padding:0.5rem;font-size:0.78rem;">
                <span style="color:#10B981;font-weight:700;">🟢 OLLAMA CONNECTED</span><br/>
                <span style="color:#CBD5E1;">Model: <strong>{active_m}</strong></span><br/>
                <span style="color:#94A3B8;">Latency: {health['latency_ms']}ms</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:6px;padding:0.5rem;font-size:0.78rem;">
                <span style="color:#F87171;font-weight:700;">🟡 DEMO / OFFLINE MODE</span><br/>
                <span style="color:#CBD5E1;">Ollama not detected at {ollama_service.base_url}</span><br/>
                <span style="color:#94A3B8;">Running heuristic engine</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

# 6. Render Main Header
render_header()

# 7. Page Routing
if nav_selection == "📊 Overview":
    if active_project:
        render_overview_page(project_service, active_project)
    else:
        st.info("No active project found. Use the **Project Planner** to create one or load the demo project.")

elif nav_selection == "🤖 Project Planner":
    render_planner_page(project_service, active_project, st.session_state["selected_model"], turbo_mode=turbo_mode)

elif nav_selection == "📋 Tasks":
    if active_project:
        render_tasks_page(project_service, active_project)
    else:
        st.info("No active project found. Please create or load a project first.")

elif nav_selection == "🚨 Blockers & Replanning":
    if active_project:
        render_blockers_page(project_service, active_project, st.session_state["selected_model"], turbo_mode=turbo_mode)
    else:
        st.info("No active project found. Please create or load a project first.")

elif nav_selection == "💬 AI Assistant":
    if active_project:
        render_assistant_page(active_project, st.session_state["selected_model"], turbo_mode=turbo_mode)
    else:
        st.info("No active project found. Please create or load a project first.")

elif nav_selection == "👥 Team":
    if active_project:
        render_team_page(project_service, active_project)
    else:
        st.info("No active project found. Please create or load a project first.")

elif nav_selection == "⚙️ Settings":
    render_settings_page(project_service, ollama_service)
