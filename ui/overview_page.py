"""Overview Page: executive summary, metrics, progress, workload, and next actions."""
import streamlit as st
import pandas as pd
from models.schemas import Project, TaskStatus
from services.project_service import ProjectService
from ui.components import render_metric_card, render_task_card


def render_overview_page(project_service: ProjectService, project: Project):
    st.markdown('<div class="section-header">📊 Project Health & Overview</div>', unsafe_allow_html=True)

    metrics = project_service.calculate_metrics(project)

    # Top Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card(
            label="Total Tasks",
            value=f"{metrics['total_tasks']}",
            subtext=f"{metrics['completed_tasks']} Completed",
            border_color="rgba(139, 92, 246, 0.4)",
        )
    with c2:
        comp_pct = metrics["completion_percentage"]
        render_metric_card(
            label="Completion",
            value=f"{comp_pct}%",
            subtext=f"{metrics['in_progress_tasks']} in progress",
            border_color="rgba(6, 182, 212, 0.5)",
        )
    with c3:
        render_metric_card(
            label="Remaining Hours",
            value=f"{metrics['remaining_estimated_hours']}h",
            subtext=f"Total: {metrics['total_estimated_hours']}h",
            border_color="rgba(245, 158, 11, 0.4)",
        )
    with c4:
        blk_count = metrics["active_blockers_count"]
        blk_color = "rgba(239, 68, 68, 0.6)" if blk_count > 0 else "rgba(16, 185, 129, 0.4)"
        render_metric_card(
            label="Active Blockers",
            value=f"{blk_count}",
            subtext="Needs attention" if blk_count > 0 else "All clear",
            border_color=blk_color,
        )

    # Overall Progress Bar
    st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
    st.caption(f"**Overall Milestone Progress ({comp_pct}% complete)**")
    st.progress(comp_pct / 100.0)

    # Overdue / Deadline Warning
    if metrics["is_overdue"]:
        st.warning(
            f"⚠️ **Timeline Overrun Risk:** Remaining estimated work ({metrics['remaining_estimated_hours']}h) "
            f"exceeds the available hackathon window ({project.deadline_hours}h). "
            f"Navigate to **Blockers & Replanning** to descope non-critical features."
        )

    # Two column layout: Team Workload & Ready Tasks
    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        st.markdown('<div class="section-header">👥 Team Workload Distribution</div>', unsafe_allow_html=True)
        workloads = metrics["member_workloads"]
        if workloads:
            for member_name, w in workloads.items():
                ratio = min(1.0, (w["active_hours"] / max(1.0, w["max_hours"])))
                st.markdown(
                    f"""
                    <div style="background:#131D31;border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:0.9rem;margin-bottom:0.7rem;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <strong>{member_name}</strong>
                            <span style="font-size:0.82rem;color:#00F0FF;">{w['active_hours']}h active / {w['done_hours']}h done</span>
                        </div>
                        <div style="font-size:0.78rem;color:#94A3B8;margin-bottom:0.4rem;">{w['role']} • {w['active_count']} tasks pending</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.progress(ratio)
        else:
            st.info("No team members configured.")

        # Next Actions Panel
        st.markdown('<div class="section-header">🎯 Recommended Next Actions</div>', unsafe_allow_html=True)
        for m in project.team_members:
            ready_for_m = [
                t for t in metrics["ready_tasks"] if t.assigned_to == m.name
            ]
            if ready_for_m:
                top = ready_for_m[0]
                st.info(f"**{m.name}** → Execute **[{top.id}] {top.title}** ({top.estimated_hours}h). All dependencies are met!")
            else:
                waiting_for_m = [
                    t for t in project.tasks if t.assigned_to == m.name and t.status == TaskStatus.TODO
                ]
                if waiting_for_m:
                    st.warning(f"**{m.name}** → Pending tasks are currently waiting on prerequisite deliverables.")
                else:
                    st.success(f"**{m.name}** → All assigned tasks completed or up to date!")

    with col_right:
        st.markdown('<div class="section-header">⚡ Ready to Execute Now</div>', unsafe_allow_html=True)
        ready_tasks = metrics["ready_tasks"]
        if ready_tasks:
            for task in ready_tasks[:3]:
                render_task_card(task, project.tasks)
            if len(ready_tasks) > 3:
                st.caption(f"+ {len(ready_tasks) - 3} more ready tasks available in the Tasks page.")
        else:
            st.info("No tasks are currently marked ready. Resolve pending dependencies or active blockers.")

        # Waiting Tasks Analysis
        waiting = metrics["waiting_tasks"]
        if waiting:
            st.markdown('<div class="section-header">⏳ Waiting on Dependencies</div>', unsafe_allow_html=True)
            for w in waiting[:3]:
                st.markdown(
                    f"""
                    <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.25);border-radius:8px;padding:0.75rem;margin-bottom:0.5rem;font-size:0.85rem;">
                        <strong>[{w['task_id']}] {w['task_title']}</strong> ({w['assigned_to']})<br/>
                        <span style="color:#F87171;">Waiting on: {', '.join(w['waiting_on'])}</span><br/>
                        <span style="color:#94A3B8;font-size:0.8rem;">👉 {w['what_needs_to_happen']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # Activity History
    st.markdown('<div class="section-header">📜 Recent Project Activity</div>', unsafe_allow_html=True)
    if project.activity_logs:
        for log in project.activity_logs[:5]:
            st.markdown(
                f"""
                <div style="font-size:0.82rem;color:#94A3B8;padding:0.35rem 0;border-bottom:1px solid rgba(255,255,255,0.04);">
                    <span style="color:#00F0FF;font-weight:600;">{log.timestamp}</span> •
                    <span style="color:#A78BFA;font-weight:600;">[{log.author}]</span>
                    <span style="color:#E2E8F0;margin-left:0.4rem;">{log.description}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.caption("No activity logged yet.")
