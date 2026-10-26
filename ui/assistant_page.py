"""AI Assistant Page: conversational, project-aware chat assistant grounded in real state."""
from typing import Optional
import streamlit as st

from models.schemas import Project
from agents.assistant import ProjectAssistantAgent


def render_assistant_page(project: Project, model_name: str, turbo_mode: bool = False):
    st.markdown('<div class="section-header">💬 AI Project Assistant</div>', unsafe_allow_html=True)
    st.caption("Ask anything about tasks, bottlenecks, deadlines, or scope. Answers are grounded in live project data.")

    # Quick prompt pills
    st.markdown("**Quick Inquiries:**")
    preset_col1, preset_col2, preset_col3 = st.columns(3)
    preset_col4, preset_col5, preset_col6 = st.columns(3)

    query_to_send = None

    with preset_col1:
        if st.button("👉 What should we work on next?", use_container_width=True):
            query_to_send = "What should we work on next?"
    with preset_col2:
        if st.button("⛔ Which tasks are blocking progress?", use_container_width=True):
            query_to_send = "Which tasks are blocking our progress?"
    with preset_col3:
        if st.button("⏱️ What can we finish in 2 hours?", use_container_width=True):
            query_to_send = "What can we finish in the next two hours?"
    with preset_col4:
        if st.button("📅 Are we on track for deadline?", use_container_width=True):
            query_to_send = "Are we on track to finish before the deadline?"
    with preset_col5:
        if st.button("✂️ Which features should we cut for MVP?", use_container_width=True):
            query_to_send = "Which features should we cut to finish the MVP?"
    with preset_col6:
        if st.button("👥 What should each member do now?", use_container_width=True):
            query_to_send = "What should each member do now?"

    # Chat history management
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = [
            {
                "role": "assistant",
                "content": f"Hello team! I'm your project assistant for **{project.name}**. I'm tracking all {len(project.tasks)} tasks, dependencies, and team capacity. How can I assist your sprint right now?",
            }
        ]

    # Display Chat Messages
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Chat Input
    user_input = st.chat_input("Ask a project question (e.g. 'Can Alex start on integration now?')...")
    if user_input:
        query_to_send = user_input

    if query_to_send:
        # Add user message
        st.session_state["chat_history"].append({"role": "user", "content": query_to_send})
        with st.chat_message("user"):
            st.markdown(query_to_send)

        # Generate Assistant response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing project graph and querying state..."):
                assistant = ProjectAssistantAgent()
                response = assistant.answer_query(
                    project=project,
                    user_query=query_to_send,
                    conversation_history=st.session_state["chat_history"],
                    model=model_name,
                    turbo_mode=turbo_mode,
                )
                st.markdown(response)
                st.session_state["chat_history"].append({"role": "assistant", "content": response})
