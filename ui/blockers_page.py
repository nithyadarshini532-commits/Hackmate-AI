"""Blockers & Replanning Page: report blockers, view inferred risks, trigger AI replanning, and approve changes."""
from typing import Optional
import streamlit as st

from models.schemas import BlockerStatus, Project, ProposalStatus, TaskStatus
from services.project_service import ProjectService
from agents.blocker_detector import BlockerDetectorAgent
from agents.replanner import ReplanningAgent
from ui.components import render_blocker_item, render_task_card


def render_blockers_page(project_service: ProjectService, project: Project, model_name: str, turbo_mode: bool = False):
    st.markdown('<div class="section-header">🚨 Blockers & AI Replanning</div>', unsafe_allow_html=True)
    st.caption("Detect bottlenecks, report hurdles, and let the AI Replanning Agent calculate an updated golden path.")

    tab_report, tab_active, tab_replan = st.tabs(
        ["📝 Report Blocker", "🛡️ Active Issues & Inferred Risks", "⚡ AI Replanning Agent"]
    )

    # TAB 1: Report New Blocker
    with tab_report:
        st.subheader("Report an Obstacle or Technical Failure")
        with st.form("report_blocker_form"):
            c1, c2 = st.columns(2)
            with c1:
                blocker_type = st.selectbox(
                    "Blocker Category",
                    [
                        "API/Library Failure",
                        "Member Unavailable",
                        "Task Delayed / Taking Too Long",
                        "Missing Dependency",
                        "Integration Failure",
                        "Hardware / Driver Issue",
                        "Other",
                    ],
                )
                member_names = [m.name for m in project.team_members] or ["User"]
                reporter = st.selectbox("Reported By", member_names)

            with c2:
                task_choices = ["None / General Project Blocker"] + [f"[{t.id}] {t.title}" for t in project.tasks]
                selected_task_opt = st.selectbox("Affected Task", task_choices)

            description = st.text_area(
                "Blocker Details",
                placeholder="Explain exactly what is failing (e.g. library throws driver error, external endpoint returning 500)...",
                height=90,
            )

            submit_blk = st.form_submit_button("🚨 File Blocker Report", type="primary", use_container_width=True)

        if submit_blk:
            if not description.strip():
                st.error("Please enter blocker details.")
                return

            affected_id = None
            if selected_task_opt != "None / General Project Blocker":
                affected_id = selected_task_opt.split("]")[0].replace("[", "").strip()

            detector = BlockerDetectorAgent()
            steps = detector.suggest_blocker_resolution(description, blocker_type)

            blocker = project_service.report_blocker(
                project=project,
                task_id=affected_id,
                reported_by=reporter,
                blocker_type=blocker_type,
                description=description,
                is_inferred=False,
                resolution_steps=steps,
            )
            st.success(f"Blocker [{blocker.id}] filed successfully! Next mitigation steps generated.")
            st.rerun()

    # TAB 2: Active Issues & Inferred Risks
    with tab_active:
        user_blockers = [b for b in project.blockers if not b.is_inferred]
        st.subheader(f"User-Reported Blockers ({len(user_blockers)})")

        active_user_b = [b for b in user_blockers if b.status == BlockerStatus.ACTIVE]
        if active_user_b:
            for b in active_user_b:
                render_blocker_item(b)
                if st.button(f"Mark [{b.id}] Resolved", key=f"resolve_{b.id}"):
                    project_service.resolve_blocker(project, b.id, author="User")
                    st.success(f"Blocker [{b.id}] marked resolved.")
                    st.rerun()
        else:
            st.success("No active user-reported blockers! All reported issues are resolved.")

        # Inferred System Risks (CRITICAL: Distinguishes from user reported)
        st.markdown("---")
        st.subheader("🔍 Automated Risk Monitor (Inferred from Graph & Timelines)")
        st.caption("These issues are detected algorithmically based on dependency graph analysis and workload meters.")

        detector = BlockerDetectorAgent()
        inferred_risks = detector.detect_inferred_risks(project)

        if inferred_risks:
            for risk in inferred_risks:
                render_blocker_item(risk)
        else:
            st.info("No inferred timeline or dependency risks detected at this time.")

    # TAB 3: AI Replanning Agent
    with tab_replan:
        st.subheader("Autonomous Schedule & Scope Replanning")
        st.markdown(
            """
            When deadlines slip or blockers occur, the **AI Replanning Agent** evaluates remaining hours,
            descopes problematic stretch goals, unlinks blocked prerequisites with mock contracts,
            and prepares a balanced revised schedule.
            """
        )

        # Trigger Replan Button
        if st.button("🔄 Generate Revised Plan with AI", type="primary", use_container_width=True):
            with st.spinner(f"Replanning Agent is analyzing blockers and generating revised schedule ({'⚡ Turbo Mode' if turbo_mode else model_name})..."):
                replanner = ReplanningAgent()
                proposal = replanner.generate_replan(project, model=model_name, turbo_mode=turbo_mode)
                project.replan_proposals.insert(0, proposal)
                project_service.storage.save_project(project)
                st.session_state["active_proposal_id"] = proposal.id
                st.success(f"New replan proposal [{proposal.id}] ready for team review!")
                st.rerun()

        # Display Pending or Recent Proposals
        pending_proposals = [p for p in project.replan_proposals if p.status == ProposalStatus.PENDING]
        active_prop = pending_proposals[0] if pending_proposals else (project.replan_proposals[0] if project.replan_proposals else None)

        if active_prop:
            st.markdown("---")
            prop_status_color = "#38BDF8" if active_prop.status == ProposalStatus.PENDING else ("#34D399" if active_prop.status == ProposalStatus.ACCEPTED else "#F87171")
            st.markdown(
                f"""
                <div style="background:rgba(15,23,42,0.8);border:1px solid rgba(139,92,246,0.4);border-radius:10px;padding:1.1rem;margin-bottom:1rem;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <h4 style="margin:0;color:#F8FAFC;">Replan Proposal: <span style="color:#00F0FF;">{active_prop.id}</span></h4>
                        <span class="badge" style="background:rgba(255,255,255,0.08);color:{prop_status_color};border:1px solid {prop_status_color};">{active_prop.status.value}</span>
                    </div>
                    <div style="font-size:0.95rem;color:#E2E8F0;margin-top:0.5rem;">{active_prop.summary}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Details: Recommended Changes, Reasons, Risks
            r_c1, r_c2 = st.columns(2)
            with r_c1:
                st.markdown("**Recommended Changes:**")
                for ch in active_prop.recommended_changes:
                    st.markdown(f"• {ch}")

                st.markdown("**Key Trade-offs & Risks:**")
                for rk in active_prop.risks_and_tradeoffs:
                    st.markdown(f"• {rk}")

            with r_c2:
                st.markdown("**Reasons for Adjustments:**")
                for re in active_prop.reasons:
                    st.markdown(f"• {re}")

                st.markdown("**Team Immediate Next Actions:**")
                for mem, act in active_prop.member_next_actions.items():
                    st.info(f"**{mem}:** {act}")

            # Previous vs Revised Plan Comparison
            st.markdown("#### 🔄 Schedule Comparison: Previous Plan vs Revised Plan")
            diff_col1, diff_col2 = st.columns(2)

            with diff_col1:
                st.caption(f"**Current Plan ({len(active_prop.previous_tasks)} tasks)**")
                for pt in active_prop.previous_tasks:
                    prio_color = "#F87171" if pt.priority.value == "High" else "#FBBF24"
                    st.markdown(
                        f"""
                        <div style="background:#131D31;border-left:3px solid {prio_color};border-radius:4px;padding:0.5rem 0.7rem;margin-bottom:0.4rem;font-size:0.83rem;">
                            <strong>[{pt.id}]</strong> {pt.title} ({pt.estimated_hours}h)<br/>
                            <span style="color:#94A3B8;">Assignee: {pt.assigned_to} • Status: {pt.status.value} • MVP: {pt.is_mvp}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            with diff_col2:
                st.caption(f"**Proposed Revised Plan ({len(active_prop.revised_tasks)} tasks)**")
                for rt in active_prop.revised_tasks:
                    prio_color = "#F87171" if rt.priority.value == "High" else "#FBBF24"
                    st.markdown(
                        f"""
                        <div style="background:#131D31;border-left:3px solid {prio_color};border-radius:4px;padding:0.5rem 0.7rem;margin-bottom:0.4rem;font-size:0.83rem;">
                            <strong>[{rt.id}]</strong> {rt.title} ({rt.estimated_hours}h)<br/>
                            <span style="color:#94A3B8;">Assignee: {rt.assigned_to} • Status: {rt.status.value} • MVP: {rt.is_mvp}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # Accept / Reject Controls (Only active if Pending)
            if active_prop.status == ProposalStatus.PENDING:
                st.markdown("---")
                a_col1, a_col2 = st.columns(2)
                with a_col1:
                    if st.button("✅ Accept & Apply This Plan to Workspace", type="primary", use_container_width=True):
                        ok, msg = project_service.apply_replan_proposal(project, active_prop.id, author="User")
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                with a_col2:
                    if st.button("❌ Reject Proposed Plan", use_container_width=True):
                        ok, msg = project_service.reject_replan_proposal(project, active_prop.id, author="User")
                        if ok:
                            st.info(msg)
                            st.rerun()
                        else:
                            st.error(msg)
        else:
            st.info("No replan proposals yet. Click 'Generate Revised Plan with AI' when ready.")
