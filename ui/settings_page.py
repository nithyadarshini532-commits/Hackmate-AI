"""Settings Page: Ollama server configuration, model selector, demo project loader, and database management."""
import streamlit as st
from services.ollama_service import OllamaService
from services.project_service import ProjectService


def render_settings_page(project_service: ProjectService, ollama_service: OllamaService):
    st.markdown('<div class="section-header">⚙️ System & AI Settings</div>', unsafe_allow_html=True)
    st.caption("Configure local Ollama connection, select LLM models, and toggle Demo Project mode for judges.")

    # Section 1: Ollama Server Status
    st.subheader("1. Local Ollama AI Engine")
    c1, c2 = st.columns([2, 1])

    with c1:
        ollama_url = st.text_input("Ollama Base URL", value=ollama_service.base_url)
        ollama_service.base_url = ollama_url.rstrip("/")

    with c2:
        st.write("")
        st.write("")
        check_conn = st.button("🔌 Test Connection", use_container_width=True)

    health = ollama_service.check_health()
    if health["connected"]:
        st.success(
            f"✅ **Ollama Connected!** Latency: `{health['latency_ms']}ms` | Installed models: `{', '.join(health['models']) or 'None'}`"
        )
    else:
        st.error(
            f"❌ **Ollama Offline:** {health['error']}\n\n"
            "Ensure Ollama is running locally (`ollama serve`). "
            "You can still use HackMate AI in Demo Mode with the smart heuristic engine."
        )

    # Model Selection
    installed_models = health["models"] if health["connected"] else []
    default_opts = ["qwen2.5:3b", "llama3.1:8b"]
    all_options = list(dict.fromkeys(installed_models + default_opts))

    current_model = st.session_state.get("selected_model", "qwen2.5:3b")
    default_idx = all_options.index(current_model) if current_model in all_options else 0

    selected = st.selectbox("Active AI Model", all_options, index=default_idx)
    st.session_state["selected_model"] = selected

    if selected not in installed_models and health["connected"]:
        st.warning(
            f"Model `{selected}` is not yet installed in local Ollama. "
            f"Run `ollama pull {selected}` in your terminal, or select an installed model."
        )

    # Section 2: Demo Mode for Hackathon Judges
    st.markdown("---")
    st.subheader("2. Judge Demonstration & Demo Project")
    st.markdown(
        """
        Load a realistic example project (**HealthPulse AI**) pre-populated with:
        - 2 team members with roles and skills
        - 8 sequential tasks with dependencies and statuses
        - A realistic hardware blocker report (Bluetooth BLE driver timeout)
        - A pre-calculated AI replan proposal ready for review
        """
    )

    if st.button("🚀 Load Hackathon Demo Project", type="primary", use_container_width=True):
        demo = project_service.load_demo()
        st.session_state["active_project_id"] = demo.id
        st.session_state["chat_history"] = [
            {
                "role": "assistant",
                "content": f"Loaded demo project **{demo.name}**. I'm tracking all {len(demo.tasks)} tasks, dependencies, and active blocker BLK-1. Ask me anything!",
            }
        ]
        st.success(f"Demo project '{demo.name}' loaded and activated! Check the Overview and Blockers tabs.")
        st.rerun()

    # Section 3: Database Operations
    st.markdown("---")
    st.subheader("3. Workspace Storage & Database")
    st.caption("All project state is persistently stored in SQLite (`data/hackmate.db`).")

    confirm_wipe = st.checkbox("I understand this will delete all saved projects and tasks permanently.")
    if st.button("🗑️ Reset Database", disabled=not confirm_wipe):
        project_service.storage.reset_database()
        if "active_project_id" in st.session_state:
            del st.session_state["active_project_id"]
        st.success("Database wiped successfully.")
        st.rerun()
