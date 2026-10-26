"""Tasks Page: interactive Kanban & list views, filtering, dependency validation, and task updates."""
from typing import List, Optional
import streamlit as st

from models.schemas import Project, Task, TaskPriority, TaskStatus
from services.dependency_service import DependencyService
from services.project_service import ProjectService
from agents.assignment import AssignmentAgent
from ui.components import render_task_card


def render_tasks_page(project_service: ProjectService, project: Project):
    st.markdown('<div class="section-header">📌 Task Management & Kanban</div>', unsafe_allow_html=True)

    if not project.tasks:
        st.info("No tasks in this project yet. Use the **Project Planner** to generate an MVP plan or load the demo project.")
        return

    # Filter and Search Bar
    f_c1, f_c2, f_c3, f_c4 = st.columns([2, 1, 1, 1])
    with f_c1:
        search_query = st.text_input("🔍 Search Tasks", placeholder="Search by title, description, or ID...").strip().lower()
    with f_c2:
        status_filter = st.selectbox("Status", ["All", "To Do", "In Progress", "Blocked", "Done"])
    with f_c3:
        member_names = ["All"] + [m.name for m in project.team_members]
        member_filter = st.selectbox("Assignee", member_names)
    with f_c4:
        readiness_filter = st.selectbox("Readiness", ["All", "Ready Now", "Waiting"])

    # Filter tasks
    filtered: List[Task] = []
    for t in project.tasks:
        if search_query and (search_query not in t.title.lower() and search_query not in t.description.lower() and search_query not in t.id.lower()):
            continue
        if status_filter != "All" and t.status.value != status_filter:
            continue
        if member_filter != "All" and t.assigned_to != member_filter:
            continue
        readiness = DependencyService.get_task_readiness(t, project.tasks)
        if readiness_filter == "Ready Now" and not readiness.is_ready:
            continue
        if readiness_filter == "Waiting" and (readiness.is_ready or t.status == TaskStatus.DONE):
            continue
        filtered.append(t)

    st.caption(f"Showing **{len(filtered)}** of **{len(project.tasks)}** tasks.")

    tab_kanban, tab_list, tab_edit = st.tabs(["📋 Kanban Board", "📜 List View", "✏️ Edit / Update Task"])

    # TAB 1: Kanban Board
    with tab_kanban:
        k_col1, k_col2, k_col3, k_col4 = st.columns(4)

        columns_spec = [
            (k_col1, "To Do", TaskStatus.TODO, "rgba(148, 163, 184, 0.2)", "#94A3B8"),
            (k_col2, "In Progress", TaskStatus.IN_PROGRESS, "rgba(59, 130, 246, 0.2)", "#60A5FA"),
            (k_col3, "Blocked", TaskStatus.BLOCKED, "rgba(239, 68, 68, 0.2)", "#F87171"),
            (k_col4, "Done", TaskStatus.DONE, "rgba(16, 185, 129, 0.2)", "#34D399"),
        ]

        for col, col_title, status_enum, bg_border, header_color in columns_spec:
            with col:
                col_tasks = [t for t in filtered if t.status == status_enum]
                st.markdown(
                    f"""
                    <div style="background:rgba(15,23,42,0.6);border-top:3px solid {header_color};border-radius:6px;padding:0.6rem 0.8rem;margin-bottom:0.8rem;">
                        <strong style="color:{header_color};">{col_title} ({len(col_tasks)})</strong>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                for t in col_tasks:
                    render_task_card(t, project.tasks)

    # TAB 2: List View
    with tab_list:
        for t in filtered:
            render_task_card(t, project.tasks)

    # TAB 3: Edit Task Controls
    with tab_edit:
        st.subheader("Edit Task Parameters & Dependencies")
        task_options = [f"[{t.id}] {t.title}" for t in project.tasks]
        selected_option = st.selectbox("Select Task to Edit", task_options)

        if selected_option:
            selected_id = selected_option.split("]")[0].replace("[", "").strip()
            task_to_edit = next((t for t in project.tasks if t.id == selected_id), None)

            if task_to_edit:
                readiness = DependencyService.get_task_readiness(task_to_edit, project.tasks)
                if not readiness.is_ready:
                    st.warning(f"⚠️ {readiness.reason}")
                else:
                    st.success("✅ " + readiness.reason)

                with st.form("edit_task_form"):
                    e_c1, e_c2 = st.columns(2)
                    with e_c1:
                        new_title = st.text_input("Title", value=task_to_edit.title)
                        status_options = [s.value for s in TaskStatus]
                        new_status_val = st.selectbox(
                            "Status", status_options, index=status_options.index(task_to_edit.status.value)
                        )
                        prio_options = [p.value for p in TaskPriority]
                        new_prio_val = st.selectbox(
                            "Priority", prio_options, index=prio_options.index(task_to_edit.priority.value)
                        )

                    with e_c2:
                        member_choices = [m.name for m in project.team_members]
                        curr_assignee_idx = (
                            member_choices.index(task_to_edit.assigned_to)
                            if task_to_edit.assigned_to in member_choices
                            else 0
                        )
                        new_assignee = st.selectbox("Assigned To", member_choices, index=curr_assignee_idx)
                        new_hours = st.number_input(
                            "Estimated Duration (hours)", min_value=0.5, max_value=48.0, value=float(task_to_edit.estimated_hours), step=0.5
                        )

                    new_notes = st.text_area("Notes / Progress Updates", value=task_to_edit.notes)

                    # Dependencies selector (all task IDs except itself)
                    other_task_ids = [t.id for t in project.tasks if t.id != task_to_edit.id]
                    default_deps = [d for d in task_to_edit.dependencies if d in other_task_ids]
                    new_deps = st.multiselect("Prerequisite Dependencies", other_task_ids, default=default_deps)

                    save_btn = st.form_submit_button("💾 Save Task Updates", type="primary", use_container_width=True)

                if save_btn:
                    new_status = TaskStatus(new_status_val)
                    new_prio = TaskPriority(new_prio_val)

                    # Update status
                    if new_status != task_to_edit.status:
                        ok_stat, stat_msg = project_service.update_task_status(
                            project=project,
                            task_id=task_to_edit.id,
                            new_status=new_status,
                            author="User",
                            notes=new_notes,
                        )
                        if not ok_stat:
                            st.error(stat_msg)
                            return

                    # Update other parameters
                    ok_det, det_msg = project_service.update_task_details(
                        project=project,
                        task_id=task_to_edit.id,
                        title=new_title,
                        assigned_to=new_assignee,
                        priority=new_prio,
                        estimated_hours=new_hours,
                        notes=new_notes,
                        dependencies=new_deps,
                        author="User",
                    )
                    if ok_det:
                        st.success("Task updated and persisted successfully!")
                        st.rerun()
                    else:
                        st.error(det_msg)
