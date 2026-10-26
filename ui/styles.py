"""Custom CSS styles and theme definitions for HackMate AI."""

THEME_CSS = """
<style>
/* Main app dark navy styling */
.stApp {
    background-color: #0B0F19;
    color: #E2E8F0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #0F172A !important;
    border-right: 1px solid rgba(139, 92, 246, 0.2);
}

/* Brand header gradient */
.brand-title {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #00F0FF 0%, #8B5CF6 50%, #D946EF 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
    margin-bottom: 0.2rem;
}

.brand-tagline {
    font-size: 1.05rem;
    color: #94A3B8;
    margin-bottom: 1.2rem;
    font-weight: 400;
}

/* Glassmorphic metric cards */
.metric-card {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
    border: 1px solid rgba(139, 92, 246, 0.25);
    border-radius: 12px;
    padding: 1.1rem 1.2rem;
    box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
    transition: transform 0.2s ease, border-color 0.2s ease;
}

.metric-card:hover {
    border-color: rgba(6, 182, 212, 0.5);
    transform: translateY(-2px);
}

.metric-value {
    font-size: 1.9rem;
    font-weight: 700;
    color: #F8FAFC;
    line-height: 1.1;
}

.metric-label {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #94A3B8;
    margin-top: 0.4rem;
}

/* Badges */
.badge {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.badge-high {
    background: rgba(239, 68, 68, 0.15);
    color: #F87171;
    border: 1px solid rgba(239, 68, 68, 0.35);
}

.badge-med {
    background: rgba(245, 158, 11, 0.15);
    color: #FBBF24;
    border: 1px solid rgba(245, 158, 11, 0.35);
}

.badge-low {
    background: rgba(16, 185, 129, 0.15);
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.35);
}

.badge-cyan {
    background: rgba(6, 182, 212, 0.15);
    color: #22D3EE;
    border: 1px solid rgba(6, 182, 212, 0.35);
}

.badge-purple {
    background: rgba(139, 92, 246, 0.15);
    color: #A78BFA;
    border: 1px solid rgba(139, 92, 246, 0.35);
}

/* Task card container */
.task-card {
    background: #131D31;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    transition: all 0.2s ease;
}

.task-card:hover {
    border-color: rgba(139, 92, 246, 0.4);
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.15);
}

.task-card-ready {
    border-left: 4px solid #10B981;
}

.task-card-blocked {
    border-left: 4px solid #EF4444;
}

.task-card-inprogress {
    border-left: 4px solid #3B82F6;
}

.task-card-done {
    border-left: 4px solid #64748B;
    opacity: 0.85;
}

/* Blocker alert callout */
.blocker-box {
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.75rem;
}

.risk-box {
    background: rgba(245, 158, 11, 0.08);
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.75rem;
}

/* Buttons */
.stButton>button {
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s ease;
}

.stButton>button:hover {
    border-color: #00F0FF;
    box-shadow: 0 0 10px rgba(0, 240, 255, 0.3);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid rgba(139, 92, 246, 0.2);
}

.stTabs [data-baseweb="tab"] {
    border-radius: 6px 6px 0 0;
    color: #94A3B8;
}

.stTabs [aria-selected="true"] {
    color: #00F0FF !important;
    border-bottom: 2px solid #00F0FF !important;
    background-color: transparent !important;
}

/* Section titles */
.section-header {
    font-size: 1.35rem;
    font-weight: 700;
    color: #F1F5F9;
    margin-top: 1rem;
    margin-bottom: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
</style>
"""


def get_status_badge_html(status: str) -> str:
    s = status.lower()
    if "done" in s:
        return '<span class="badge" style="background:rgba(16,185,129,0.2);color:#34D399;border:1px solid #10B981">DONE</span>'
    elif "in progress" in s:
        return '<span class="badge" style="background:rgba(59,130,246,0.2);color:#60A5FA;border:1px solid #3B82F6">IN PROGRESS</span>'
    elif "blocked" in s:
        return '<span class="badge" style="background:rgba(239,68,68,0.2);color:#F87171;border:1px solid #EF4444">BLOCKED</span>'
    else:
        return '<span class="badge" style="background:rgba(148,163,184,0.15);color:#CBD5E1;border:1px solid #64748B">TO DO</span>'


def get_priority_badge_html(priority: str) -> str:
    p = priority.lower()
    if "high" in p:
        return '<span class="badge badge-high">HIGH</span>'
    elif "low" in p:
        return '<span class="badge badge-low">LOW</span>'
    else:
        return '<span class="badge badge-med">MEDIUM</span>'
