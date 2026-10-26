"""SQLite persistent storage service for HackMate AI."""
import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from models.schemas import (
    ActivityLog,
    Blocker,
    BlockerStatus,
    Project,
    ProposalStatus,
    ReplanProposal,
    Task,
    TaskPriority,
    TaskStatus,
    TeamMember,
)

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "hackmate.db"
)


class StorageService:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Projects table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    idea TEXT NOT NULL,
                    problem_statement TEXT,
                    category TEXT,
                    deadline_hours REAL,
                    team_size INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                )
            """
            )

            # Team members table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS team_members (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT,
                    skills_json TEXT,
                    max_hours REAL,
                    current_workload_hours REAL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """
            )

            # Tasks table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority TEXT,
                    assigned_to TEXT,
                    estimated_hours REAL,
                    status TEXT,
                    dependencies_json TEXT,
                    acceptance_criteria_json TEXT,
                    suggested_order INTEGER,
                    notes TEXT,
                    is_mvp INTEGER,
                    PRIMARY KEY(id, project_id),
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """
            )

            # Blockers table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS blockers (
                    id TEXT,
                    project_id TEXT NOT NULL,
                    task_id TEXT,
                    reported_by TEXT,
                    blocker_type TEXT,
                    description TEXT NOT NULL,
                    is_inferred INTEGER DEFAULT 0,
                    status TEXT,
                    resolution_steps_json TEXT,
                    created_at TEXT,
                    resolved_at TEXT,
                    PRIMARY KEY(id, project_id),
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """
            )

            # Replan Proposals table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS replan_proposals (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    summary TEXT,
                    previous_tasks_json TEXT,
                    revised_tasks_json TEXT,
                    recommended_changes_json TEXT,
                    reasons_json TEXT,
                    risks_and_tradeoffs_json TEXT,
                    member_next_actions_json TEXT,
                    status TEXT,
                    created_at TEXT,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """
            )

            # Activity Logs table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    timestamp TEXT,
                    action_type TEXT,
                    description TEXT,
                    author TEXT,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """
            )

            conn.commit()

    def save_project(self, project: Project) -> None:
        """Saves or updates a project and its associated entities atomically."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Upsert Project
            cursor.execute(
                """
                INSERT INTO projects (id, name, idea, problem_statement, category, deadline_hours, team_size, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    idea=excluded.idea,
                    problem_statement=excluded.problem_statement,
                    category=excluded.category,
                    deadline_hours=excluded.deadline_hours,
                    team_size=excluded.team_size,
                    updated_at=excluded.updated_at
            """,
                (
                    project.id,
                    project.name,
                    project.idea,
                    project.problem_statement,
                    project.category,
                    project.deadline_hours,
                    project.team_size,
                    project.created_at,
                    project.updated_at,
                ),
            )

            # 2. Team Members: clear old, insert current
            cursor.execute("DELETE FROM team_members WHERE project_id = ?", (project.id,))
            for m in project.team_members:
                cursor.execute(
                    """
                    INSERT INTO team_members (id, project_id, name, role, skills_json, max_hours, current_workload_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        m.id,
                        project.id,
                        m.name,
                        m.role,
                        json.dumps(m.skills),
                        m.max_hours,
                        m.current_workload_hours,
                    ),
                )

            # 3. Tasks: clear old, insert current
            cursor.execute("DELETE FROM tasks WHERE project_id = ?", (project.id,))
            for t in project.tasks:
                cursor.execute(
                    """
                    INSERT INTO tasks (
                        id, project_id, title, description, priority, assigned_to,
                        estimated_hours, status, dependencies_json, acceptance_criteria_json,
                        suggested_order, notes, is_mvp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        t.id,
                        project.id,
                        t.title,
                        t.description,
                        t.priority.value,
                        t.assigned_to,
                        t.estimated_hours,
                        t.status.value,
                        json.dumps(t.dependencies),
                        json.dumps(t.acceptance_criteria),
                        t.suggested_order,
                        t.notes,
                        1 if t.is_mvp else 0,
                    ),
                )

            # 4. Blockers: clear old, insert current
            cursor.execute("DELETE FROM blockers WHERE project_id = ?", (project.id,))
            for b in project.blockers:
                cursor.execute(
                    """
                    INSERT INTO blockers (
                        id, project_id, task_id, reported_by, blocker_type, description,
                        is_inferred, status, resolution_steps_json, created_at, resolved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        b.id,
                        project.id,
                        b.task_id,
                        b.reported_by,
                        b.blocker_type,
                        b.description,
                        1 if b.is_inferred else 0,
                        b.status.value,
                        json.dumps(b.resolution_steps),
                        b.created_at,
                        b.resolved_at,
                    ),
                )

            # 5. Replan Proposals
            cursor.execute("DELETE FROM replan_proposals WHERE project_id = ?", (project.id,))
            seen_proposals = set()
            for p in project.replan_proposals:
                if p.id in seen_proposals:
                    continue
                seen_proposals.add(p.id)
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO replan_proposals (
                        id, project_id, summary, previous_tasks_json, revised_tasks_json,
                        recommended_changes_json, reasons_json, risks_and_tradeoffs_json,
                        member_next_actions_json, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        p.id,
                        project.id,
                        p.summary,
                        json.dumps([t.model_dump() for t in p.previous_tasks]),
                        json.dumps([t.model_dump() for t in p.revised_tasks]),
                        json.dumps(p.recommended_changes),
                        json.dumps(p.reasons),
                        json.dumps(p.risks_and_tradeoffs),
                        json.dumps(p.member_next_actions),
                        p.status.value,
                        p.created_at,
                    ),
                )

            # 6. Activity logs
            cursor.execute("DELETE FROM activity_logs WHERE project_id = ?", (project.id,))
            for a in project.activity_logs:
                cursor.execute(
                    """
                    INSERT INTO activity_logs (id, project_id, timestamp, action_type, description, author)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (a.id, project.id, a.timestamp, a.action_type, a.description, a.author),
                )

            conn.commit()

    def get_project(self, project_id: str) -> Optional[Project]:
        """Loads a project and all its entities by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            if not row:
                return None

            # Team members
            cursor.execute(
                "SELECT * FROM team_members WHERE project_id = ? ORDER BY id ASC", (project_id,)
            )
            member_rows = cursor.fetchall()
            members: List[TeamMember] = []
            for mr in member_rows:
                members.append(
                    TeamMember(
                        id=mr["id"],
                        name=mr["name"],
                        role=mr["role"] or "Developer",
                        skills=json.loads(mr["skills_json"]) if mr["skills_json"] else [],
                        max_hours=mr["max_hours"] or 24.0,
                        current_workload_hours=mr["current_workload_hours"] or 0.0,
                    )
                )

            # Tasks
            cursor.execute(
                "SELECT * FROM tasks WHERE project_id = ? ORDER BY suggested_order ASC, id ASC",
                (project_id,),
            )
            task_rows = cursor.fetchall()
            tasks: List[Task] = []
            for tr in task_rows:
                tasks.append(
                    Task(
                        id=tr["id"],
                        title=tr["title"],
                        description=tr["description"] or "",
                        priority=TaskPriority(tr["priority"]),
                        assigned_to=tr["assigned_to"] or "Unassigned",
                        estimated_hours=tr["estimated_hours"] or 2.0,
                        status=TaskStatus(tr["status"]),
                        dependencies=json.loads(tr["dependencies_json"])
                        if tr["dependencies_json"]
                        else [],
                        acceptance_criteria=json.loads(tr["acceptance_criteria_json"])
                        if tr["acceptance_criteria_json"]
                        else [],
                        suggested_order=tr["suggested_order"] or 1,
                        notes=tr["notes"] or "",
                        is_mvp=bool(tr["is_mvp"]),
                    )
                )

            # Blockers
            cursor.execute(
                "SELECT * FROM blockers WHERE project_id = ? ORDER BY created_at DESC", (project_id,)
            )
            blocker_rows = cursor.fetchall()
            blockers: List[Blocker] = []
            for br in blocker_rows:
                blockers.append(
                    Blocker(
                        id=br["id"],
                        task_id=br["task_id"],
                        reported_by=br["reported_by"] or "System",
                        blocker_type=br["blocker_type"] or "Other",
                        description=br["description"],
                        is_inferred=bool(br["is_inferred"]),
                        status=BlockerStatus(br["status"]),
                        resolution_steps=json.loads(br["resolution_steps_json"])
                        if br["resolution_steps_json"]
                        else [],
                        created_at=br["created_at"],
                        resolved_at=br["resolved_at"],
                    )
                )

            # Replan Proposals
            cursor.execute(
                "SELECT * FROM replan_proposals WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            )
            proposal_rows = cursor.fetchall()
            proposals: List[ReplanProposal] = []
            for pr in proposal_rows:
                prev_t = [
                    Task(**item) for item in json.loads(pr["previous_tasks_json"])
                ] if pr["previous_tasks_json"] else []
                rev_t = [
                    Task(**item) for item in json.loads(pr["revised_tasks_json"])
                ] if pr["revised_tasks_json"] else []
                proposals.append(
                    ReplanProposal(
                        id=pr["id"],
                        project_id=pr["project_id"],
                        summary=pr["summary"] or "",
                        previous_tasks=prev_t,
                        revised_tasks=rev_t,
                        recommended_changes=json.loads(pr["recommended_changes_json"])
                        if pr["recommended_changes_json"]
                        else [],
                        reasons=json.loads(pr["reasons_json"]) if pr["reasons_json"] else [],
                        risks_and_tradeoffs=json.loads(pr["risks_and_tradeoffs_json"])
                        if pr["risks_and_tradeoffs_json"]
                        else [],
                        member_next_actions=json.loads(pr["member_next_actions_json"])
                        if pr["member_next_actions_json"]
                        else {},
                        status=ProposalStatus(pr["status"]),
                        created_at=pr["created_at"],
                    )
                )

            # Activity Logs
            cursor.execute(
                "SELECT * FROM activity_logs WHERE project_id = ? ORDER BY timestamp DESC",
                (project_id,),
            )
            log_rows = cursor.fetchall()
            logs: List[ActivityLog] = []
            for lr in log_rows:
                logs.append(
                    ActivityLog(
                        id=lr["id"],
                        timestamp=lr["timestamp"],
                        action_type=lr["action_type"],
                        description=lr["description"],
                        author=lr["author"] or "System",
                    )
                )

            return Project(
                id=row["id"],
                name=row["name"],
                idea=row["idea"],
                problem_statement=row["problem_statement"] or "",
                category=row["category"] or "AI & Agents",
                deadline_hours=row["deadline_hours"] or 24.0,
                team_size=row["team_size"] or 2,
                team_members=members,
                tasks=tasks,
                blockers=blockers,
                replan_proposals=proposals,
                activity_logs=logs,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def list_projects(self) -> List[Dict[str, str]]:
        """Returns minimal info for all projects."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, category, updated_at FROM projects ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "category": r["category"],
                    "updated_at": r["updated_at"],
                }
                for r in rows
            ]

    def delete_project(self, project_id: str) -> None:
        """Deletes a project and cascaded records."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()

    def reset_database(self) -> None:
        """Wipes all tables for a fresh state."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM activity_logs")
            cursor.execute("DELETE FROM replan_proposals")
            cursor.execute("DELETE FROM blockers")
            cursor.execute("DELETE FROM tasks")
            cursor.execute("DELETE FROM team_members")
            cursor.execute("DELETE FROM projects")
            conn.commit()
