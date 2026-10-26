"""Planner Page: interactive project intake form, AI plan generation, and plan activation."""
from typing import List, Optional
import streamlit as st

from models.schemas import Project, Task, TeamMember
from services.project_service import ProjectService
from agents.planner import PlannerAgent
from agents.assignment import AssignmentAgent
from ui.styles import get_priority_badge_html


def render_planner_page(project_service: ProjectService, active_project: Optional[Project], model_name: str, turbo_mode: bool = False):
    st.markdown('<div class="section-header">🤖 AI Project Planner</div>', unsafe_allow_html=True)
    st.caption("Transform any hackathon idea into a structured, dependency-validated MVP plan in seconds.")

    with st.form("project_planner_form"):
        st.subheader("1. Project Concept & Constraints")
        c1, c2 = st.columns([2, 1])
        with c1:
            project_name = st.text_input("Project Name", value="NeuroSync AI", placeholder="e.g. HealthPulse AI, CodeBuddy")
        with c2:
            category = st.selectbox(
                "Category",
                [
                    "AI & Agents",
                    "Healthcare & BioTech",
                    "Developer Tools & Infra",
                    "FinTech & DeFi",
                    "Education & Accessibility",
                    "Climate & Sustainability",
                    "Cybersecurity",
                    "Other",
                ],
            )

        idea = st.text_area(
            "Project Idea & Solution",
            value="A multimodal agent that analyzes user attention and ambient distractions to dynamically organize coding tasks and trigger focus rest cycles.",
            help="Describe the core problem you are solving and your technical solution.",
            height=85,
        )

        problem_statement = st.text_area(
            "Detailed Problem Statement (Optional)",
            value="Developers lose hours of deep focus due to context switching and untracked cognitive fatigue during high-stress sprint periods.",
            height=60,
        )

        deadline_hours = st.slider("Hackathon Available Duration (Hours)", min_value=6, max_value=72, value=24, step=2)

        st.subheader("2. Team Roster (2 Members)")
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown("**Member 1 (Frontend / UX)**")
            m1_name = st.text_input("Name", value="Alex Rivera", key="m1_name")
            m1_role = st.text_input("Role", value="Frontend, UI & Integration", key="m1_role")
            m1_skills = st.text_input("Skills (comma-separated)", value="Streamlit, Python, UI/UX, Plotly, CSS", key="m1_skills")

        with t_col2:
            st.markdown("**Member 2 (Backend / AI)**")
            m2_name = st.text_input("Name", value="Sam Chen", key="m2_name")
            m2_role = st.text_input("Role", value="AI Models, Backend & Core Logic", key="m2_role")
            m2_skills = st.text_input("Skills (comma-separated)", value="Python, Ollama, FastAPI, SQLite, Pydantic", key="m2_skills")

        submitted = st.form_submit_button("🚀 Generate Project Plan with AI", use_container_width=True)

    # Process Form Submission
    if submitted:
        if not project_name.strip() or not idea.strip():
            st.error("Please provide both a Project Name and an Idea.")
            return

        m1 = TeamMember(
            id="M1",
            name=m1_name.strip() or "Member 1",
            role=m1_role.strip() or "Frontend Developer",
            skills=[s.strip() for s in m1_skills.split(",") if s.strip()],
            max_hours=float(deadline_hours),
        )
        m2 = TeamMember(
            id="M2",
            name=m2_name.strip() or "Member 2",
            role=m2_role.strip() or "Backend Developer",
            skills=[s.strip() for s in m2_skills.split(",") if s.strip()],
            max_hours=float(deadline_hours),
        )

        with st.spinner(f"Agentic Planner is generating MVP task hierarchy ({'⚡ Turbo Mode' if turbo_mode else model_name})..."):
            planner = PlannerAgent()
            tasks, source_msg, is_real_ai = planner.generate_plan(
                name=project_name,
                idea=idea,
                problem_statement=problem_statement,
                category=category,
                deadline_hours=float(deadline_hours),
                team_members=[m1, m2],
                model=model_name,
                turbo_mode=turbo_mode,
            )

            # Store in session state for review
            st.session_state["staged_plan"] = {
                "name": project_name,
                "idea": idea,
                "problem_statement": problem_statement,
                "category": category,
                "deadline_hours": float(deadline_hours),
                "team_members": [m1, m2],
                "tasks": tasks,
                "source_msg": source_msg,
                "is_real_ai": is_real_ai,
            }

    # Review Staged Plan
    if "staged_plan" in st.session_state:
        plan = st.session_state["staged_plan"]
        st.markdown("---")
        st.markdown('<div class="section-header">📋 Review Generated Plan</div>', unsafe_allow_html=True)

        if plan["is_real_ai"]:
            st.success(f"✨ **AI Plan Generated:** {plan['source_msg']}")
        else:
            st.info(f"ℹ️ **Smart Heuristic Engine:** {plan['source_msg']}")

        total_est = sum(t.estimated_hours for t in plan["tasks"])
        st.caption(f"**Total Tasks:** {len(plan['tasks'])} | **Estimated Duration:** {total_est:.1f}h / {plan['deadline_hours']}h")

        # Display Tasks Table
        table_data = []
        for t in plan["tasks"]:
            table_data.append(
                {
                    "Order": t.suggested_order,
                    "ID": t.id,
                    "Title": t.title,
                    "Priority": t.priority.value,
                    "Assignee": t.assigned_to,
                    "Est (hrs)": t.estimated_hours,
                    "Dependencies": ", ".join(t.dependencies) if t.dependencies else "None",
                    "MVP": "Yes" if t.is_mvp else "Stretch",
                }
            )
        st.dataframe(table_data, use_container_width=True, hide_index=True)

        # Plan Acceptance
        col_acc1, col_acc2 = st.columns([1, 1])
        with col_acc1:
            if st.button("✅ Accept & Activate This Project Plan", type="primary", use_container_width=True):
                new_project = project_service.create_project(
                    name=plan["name"],
                    idea=plan["idea"],
                    problem_statement=plan["problem_statement"],
                    category=plan["category"],
                    deadline_hours=plan["deadline_hours"],
                    team_members=plan["team_members"],
                    tasks=plan["tasks"],
                )
                st.session_state["active_project_id"] = new_project.id
                del st.session_state["staged_plan"]
                st.success(f"Project '{new_project.name}' successfully saved and activated!")
                st.rerun()

        with col_acc2:
            if st.button("❌ Discard Plan", use_container_width=True):
                del st.session_state["staged_plan"]
                st.info("Plan discarded.")
                st.rerun()
