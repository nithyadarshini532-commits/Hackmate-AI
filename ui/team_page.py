"""Team Page: member profiles, workload meters, task ownership, and collaboration workspace."""
import streamlit as st
from datetime import datetime

from models.schemas import ActivityLog, Project, TaskStatus
from services.dependency_service import DependencyService
from services.project_service import ProjectService


def render_team_page(project_service: ProjectService, project: Project):
    st.markdown('<div class="section-header">👥 Team Collaboration & Roster</div>', unsafe_allow_html=True)
    st.caption("Track individual capacity, member ownership, and log team notes for your 2-member sprint.")

    st.info(
        "💡 **Collaboration Note:** HackMate AI operates in single-machine shared workspace mode for this hackathon MVP. Simultaneous multi-device real-time sync is not implemented."
    )

    t_cols = st.columns(len(project.team_members) if project.team_members else 1)

    for idx, member in enumerate(project.team_members):
        with t_cols[idx]:
            assigned_tasks = [t for t in project.tasks if t.assigned_to == member.name]
            active_tasks = [t for t in assigned_tasks if t.status != TaskStatus.DONE]
            done_tasks = [t for t in assigned_tasks if t.status == TaskStatus.DONE]

            active_hrs = sum(t.estimated_hours for t in active_tasks)
            done_hrs = sum(t.estimated_hours for t in done_tasks)
            total_hrs = active_hrs + done_hrs

            skills_html = "".join(
                [f'<span class="badge badge-purple" style="margin:2px;">{s}</span>' for s in member.skills]
            )

            # Ready task for this member
            ready_task = next(
                (
                    t
                    for t in active_tasks
                    if DependencyService.get_task_readiness(t, project.tasks).is_ready
                ),
                None,
            )

            next_action_str = (
                f"Work on **[{ready_task.id}] {ready_task.title}**"
                if ready_task
                else ("All assigned tasks done or waiting on team prerequisites." if active_tasks else "All done!")
            )

            st.markdown(
                f"""
                <div style="background:#131D31;border:1px solid rgba(139,92,246,0.3);border-radius:10px;padding:1.1rem;margin-bottom:1rem;">
                    <h3 style="margin:0;color:#F8FAFC;">{member.name}</h3>
                    <div style="color:#00F0FF;font-size:0.88rem;margin-bottom:0.6rem;">{member.role}</div>
                    <div style="margin-bottom:0.8rem;">{skills_html}</div>
                    <div style="display:flex;justify-content:space-between;font-size:0.82rem;color:#94A3B8;margin-bottom:0.3rem;">
                        <span>Active: <strong>{active_hrs:.1f}h</strong></span>
                        <span>Done: <strong>{done_hrs:.1f}h</strong></span>
                        <span>Max Cap: <strong>{member.max_hours:.0f}h</strong></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Progress bar for workload capacity
            ratio = min(1.0, active_hrs / max(1.0, member.max_hours))
            st.progress(ratio)

            st.markdown(f"**Immediate Next Action:**")
            st.success(next_action_str)

            # Assigned tasks expander
            with st.expander(f"View Assigned Tasks ({len(assigned_tasks)})"):
                for t in assigned_tasks:
                    st.markdown(
                        f"• **[{t.id}]** {t.title} — `{t.status.value}` ({t.estimated_hours}h)"
                    )

    # Team Notes & Workspace Activity
    st.markdown("---")
    st.markdown('<div class="section-header">📝 Shared Team Notes & Log</div>', unsafe_allow_html=True)

    with st.form("add_team_note_form"):
        c1, c2 = st.columns([1, 3])
        with c1:
            member_names = [m.name for m in project.team_members] or ["User"]
            note_author = st.selectbox("Author", member_names)
        with c2:
            note_content = st.text_input("New Note or Sprint Handoff Message", placeholder="e.g., API schemas finalized in repo; ready for Alex...")

        submit_note = st.form_submit_button("📌 Post Team Note")

    if submit_note and note_content.strip():
        new_log = ActivityLog(
            id=f"note-{datetime.now().strftime('%H%M%S')}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action_type="TEAM_NOTE",
            description=f"Note: {note_content.strip()}",
            author=note_author,
        )
        project.activity_logs.insert(0, new_log)
        project_service.storage.save_project(project)
        st.success("Note added to project activity history!")
        st.rerun()

    # Timeline display
    for log in project.activity_logs[:8]:
        st.markdown(
            f"""
            <div style="font-size:0.85rem;color:#94A3B8;padding:0.4rem 0;border-bottom:1px solid rgba(255,255,255,0.05);">
                <span style="color:#00F0FF;font-weight:600;">{log.timestamp}</span> •
                <strong style="color:#A78BFA;">{log.author}</strong>:
                <span style="color:#F1F5F9;">{log.description}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
