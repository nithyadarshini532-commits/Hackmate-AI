"""Reusable UI components and widgets for HackMate AI."""
from typing import Callable, List, Optional
import streamlit as st

from models.schemas import ActivityLog, Blocker, BlockerStatus, Task, TaskStatus
from services.dependency_service import DependencyService
from ui.styles import get_priority_badge_html, get_status_badge_html


def render_header():
    """Renders the top branding and header bar."""
    st.markdown(
        """
        <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 0.5rem; margin-bottom: 1.2rem; border-bottom: 1px solid rgba(139, 92, 246, 0.2);">
            <div>
                <div class="brand-title">⚡ HackMate AI</div>
                <div class="brand-tagline">Plan smarter. Build together. Adapt faster.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, subtext: str = "", border_color: str = "rgba(139, 92, 246, 0.4)"):
    """Renders a styled dark metric card."""
    st.markdown(
        f"""
        <div class="metric-card" style="border-color: {border_color};">
            <div class="metric-value">{value}</div>
            <div class="metric-label">{label}</div>
            {f'<div style="font-size:0.8rem;color:#00F0FF;margin-top:0.25rem;">{subtext}</div>' if subtext else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_task_card(task: Task, all_tasks: List[Task]):
    """Renders a single rich task card with readiness indicators."""
    readiness = DependencyService.get_task_readiness(task, all_tasks)

    # Card border highlight
    css_class = "task-card-ready"
    indicator_text = "🟢 READY TO EXECUTE"
    if task.status == TaskStatus.DONE:
        css_class = "task-card-done"
        indicator_text = "✓ COMPLETED"
    elif task.status == TaskStatus.BLOCKED:
        css_class = "task-card-blocked"
        indicator_text = "⛔ BLOCKED"
    elif not readiness.is_ready:
        css_class = "task-card-blocked"
        indicator_text = "⏳ WAITING ON PREREQUISITES"
    elif task.status == TaskStatus.IN_PROGRESS:
        css_class = "task-card-inprogress"
        indicator_text = "⚡ IN PROGRESS"

    status_badge = get_status_badge_html(task.status.value)
    prio_badge = get_priority_badge_html(task.priority.value)
    mvp_badge = '<span class="badge badge-purple">MVP</span>' if task.is_mvp else '<span class="badge" style="background:rgba(255,255,255,0.06);color:#94A3B8;">STRETCH</span>'

    deps_str = ", ".join(task.dependencies) if task.dependencies else "None"

    st.markdown(
        f"""
        <div class="task-card {css_class}">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.4rem;">
                <div>
                    <span style="font-weight: 700; color: #00F0FF; font-size: 0.95rem; margin-right: 0.5rem;">[{task.id}]</span>
                    <span style="font-weight: 600; font-size: 1.05rem; color: #F8FAFC;">{task.title}</span>
                </div>
                <div style="display: flex; gap: 0.4rem; align-items: center;">
                    {mvp_badge}
                    {prio_badge}
                    {status_badge}
                </div>
            </div>
            <div style="font-size: 0.88rem; color: #94A3B8; margin-bottom: 0.6rem;">{task.description}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; color: #CBD5E1; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 0.5rem;">
                <div>
                    <span>👤 <strong>{task.assigned_to}</strong></span>
                    <span style="margin-left: 1rem;">⏱️ <strong>{task.estimated_hours}h</strong></span>
                    <span style="margin-left: 1rem;">🔗 Dependencies: <span style="color:#A78BFA">{deps_str}</span></span>
                </div>
                <div style="font-weight: 600; font-size: 0.78rem;">
                    {indicator_text}
                </div>
            </div>
            {f'<div style="font-size: 0.8rem; color: #F59E0B; margin-top: 0.4rem;">📝 {task.notes}</div>' if task.notes else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_blocker_item(blocker: Blocker):
    """Renders a blocker card distinguishing user-reported from inferred risks."""
    box_class = "risk-box" if blocker.is_inferred else "blocker-box"
    type_label = "AUTOMATED RISK" if blocker.is_inferred else "REPORTED BLOCKER"
    badge_color = "#F59E0B" if blocker.is_inferred else "#EF4444"

    steps_html = ""
    if blocker.resolution_steps:
        steps_items = "".join([f"<li>{s}</li>" for s in blocker.resolution_steps])
        steps_html = f"""
        <div style="margin-top: 0.5rem; font-size: 0.82rem; color: #E2E8F0;">
            <strong>Recommended Next Steps:</strong>
            <ul style="margin: 0.2rem 0 0 1.2rem; padding: 0;">
                {steps_items}
            </ul>
        </div>
        """

    task_ref = f" (Task: {blocker.task_id})" if blocker.task_id else ""
    status_label = f'<span class="badge" style="background:rgba(16,185,129,0.2);color:#34D399;font-size:0.7rem;">RESOLVED</span>' if blocker.status == BlockerStatus.RESOLVED else f'<span class="badge" style="background:rgba(239,68,68,0.2);color:#F87171;font-size:0.7rem;">ACTIVE</span>'

    st.markdown(
        f"""
        <div class="{box_class}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                <div>
                    <span style="font-weight: 700; color: {badge_color}; font-size: 0.8rem; text-transform: uppercase;">[{type_label}]</span>
                    <strong style="color: #F8FAFC; margin-left: 0.4rem;">{blocker.id}{task_ref}</strong>
                    <span style="color: #94A3B8; font-size: 0.8rem; margin-left: 0.5rem;">— Type: {blocker.blocker_type}</span>
                </div>
                <div>{status_label}</div>
            </div>
            <div style="font-size: 0.9rem; color: #CBD5E1;">{blocker.description}</div>
            <div style="font-size: 0.78rem; color: #94A3B8; margin-top: 0.3rem;">Reported by: <strong>{blocker.reported_by}</strong></div>
            {steps_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
