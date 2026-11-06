import sqlite3
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from .config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: Path = settings.DATABASE_PATH):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Creates the initial database schema if not present."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Workflows table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                objective TEXT NOT NULL,
                status TEXT NOT NULL,
                plan_json TEXT,
                total_tasks INTEGER DEFAULT 0,
                completed_tasks INTEGER DEFAULT 0,
                failed_tasks INTEGER DEFAULT 0,
                duration_seconds REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)

            # Tasks table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                task_order INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                tool_name TEXT NOT NULL,
                status TEXT NOT NULL,
                dependencies_json TEXT,
                parameters_json TEXT,
                expected_output_json TEXT,
                actual_output_json TEXT,
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,
                execution_time_ms REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
            );
            """)

            # Tool Calls table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_calls (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                input_params_json TEXT,
                output_data_json TEXT,
                success INTEGER NOT NULL,
                error_message TEXT,
                duration_ms REAL DEFAULT 0.0,
                timestamp TEXT NOT NULL
            );
            """)

            # Verification Records table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS verifications (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                status TEXT NOT NULL,
                expected_result TEXT,
                actual_result TEXT,
                checks_passed INTEGER NOT NULL,
                checks_failed INTEGER NOT NULL,
                detected_errors_json TEXT,
                explanation TEXT,
                suggested_recovery TEXT,
                timestamp TEXT NOT NULL
            );
            """)

            # Artifacts table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                task_id TEXT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                file_type TEXT,
                created_at TEXT NOT NULL
            );
            """)

            # Logs table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                task_id TEXT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                details_json TEXT,
                timestamp TEXT NOT NULL
            );
            """)

            # Evaluation metrics table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id TEXT PRIMARY KEY,
                suite_name TEXT NOT NULL,
                total_scenarios INTEGER NOT NULL,
                passed_scenarios INTEGER NOT NULL,
                metrics_json TEXT NOT NULL,
                scenario_results_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)

            conn.commit()

    # Workflow persistence
    def create_workflow(self, workflow_id: str, objective: str, plan_json: Optional[str] = None):
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO workflows (id, objective, status, plan_json, created_at, updated_at)
                VALUES (?, ?, 'PENDING', ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    objective = excluded.objective,
                    status = 'PENDING',
                    plan_json = excluded.plan_json,
                    updated_at = excluded.updated_at
                """,
                (workflow_id, objective, plan_json, now, now)
            )
            conn.commit()

    def update_workflow_status(self, workflow_id: str, status: str, plan_json: Optional[str] = None,
                               total_tasks: int = 0, completed_tasks: int = 0, failed_tasks: int = 0,
                               duration_seconds: float = 0.0):
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE workflows
                SET status = ?,
                    plan_json = COALESCE(?, plan_json),
                    total_tasks = ?,
                    completed_tasks = ?,
                    failed_tasks = ?,
                    duration_seconds = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (status, plan_json, total_tasks, completed_tasks, failed_tasks, duration_seconds, now, workflow_id)
            )
            conn.commit()

    def get_workflow(self, workflow_id: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def list_workflows(self, limit: int = 20) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM workflows ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]

    # Tasks persistence
    def upsert_task(self, task_data: dict):
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                    id, workflow_id, task_id, task_order, title, description,
                    tool_name, status, dependencies_json, parameters_json,
                    expected_output_json, actual_output_json, retry_count,
                    error_message, execution_time_ms, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    parameters_json = excluded.parameters_json,
                    actual_output_json = excluded.actual_output_json,
                    retry_count = excluded.retry_count,
                    error_message = excluded.error_message,
                    execution_time_ms = excluded.execution_time_ms,
                    updated_at = excluded.updated_at
                """,
                (
                    f"{task_data['workflow_id']}_{task_data['task_id']}",
                    task_data["workflow_id"],
                    task_data["task_id"],
                    task_data.get("task_order", 0),
                    task_data.get("title", ""),
                    task_data.get("description", ""),
                    task_data.get("tool_name", ""),
                    task_data.get("status", "PENDING"),
                    json.dumps(task_data.get("dependencies", [])),
                    json.dumps(task_data.get("parameters", {})),
                    json.dumps(task_data.get("expected_output", {})),
                    json.dumps(task_data.get("actual_output", {})),
                    task_data.get("retry_count", 0),
                    task_data.get("error_message"),
                    task_data.get("execution_time_ms", 0.0),
                    now,
                    now
                )
            )
            conn.commit()

    def get_workflow_tasks(self, workflow_id: str) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tasks WHERE workflow_id = ? ORDER BY task_order ASC",
                (workflow_id,)
            )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["dependencies"] = json.loads(item["dependencies_json"] or "[]")
                item["parameters"] = json.loads(item["parameters_json"] or "{}")
                item["expected_output"] = json.loads(item["expected_output_json"] or "{}")
                item["actual_output"] = json.loads(item["actual_output_json"] or "{}")
                results.append(item)
            return results

    # Tool calls & Verifications
    def log_tool_call(self, tool_call: dict):
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tool_calls (
                    id, task_id, workflow_id, tool_name, input_params_json,
                    output_data_json, success, error_message, duration_ms, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tool_call.get("id", str(datetime.now().timestamp())),
                    tool_call.get("task_id", ""),
                    tool_call.get("workflow_id", ""),
                    tool_call.get("tool_name", ""),
                    json.dumps(tool_call.get("input_params", {})),
                    json.dumps(tool_call.get("output_data", {})),
                    1 if tool_call.get("success", False) else 0,
                    tool_call.get("error_message"),
                    tool_call.get("duration_ms", 0.0),
                    now
                )
            )
            conn.commit()

    def get_workflow_tool_calls(self, workflow_id: str) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tool_calls WHERE workflow_id = ? ORDER BY timestamp ASC", (workflow_id,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["input_params"] = json.loads(item["input_params_json"] or "{}")
                item["output_data"] = json.loads(item["output_data_json"] or "{}")
                results.append(item)
            return results

    def save_verification(self, verif: dict):
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO verifications (
                    id, task_id, workflow_id, status, expected_result, actual_result,
                    checks_passed, checks_failed, detected_errors_json, explanation,
                    suggested_recovery, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    verif.get("id", f"v_{datetime.now().timestamp()}"),
                    verif.get("task_id", ""),
                    verif.get("workflow_id", ""),
                    verif.get("status", "PASSED"),
                    str(verif.get("expected_result", "")),
                    str(verif.get("actual_result", "")),
                    verif.get("checks_passed", 0),
                    verif.get("checks_failed", 0),
                    json.dumps(verif.get("detected_errors", [])),
                    verif.get("explanation", ""),
                    verif.get("suggested_recovery", ""),
                    now
                )
            )
            conn.commit()

    def get_workflow_verifications(self, workflow_id: str) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM verifications WHERE workflow_id = ? ORDER BY timestamp ASC", (workflow_id,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["detected_errors"] = json.loads(item["detected_errors_json"] or "[]")
                results.append(item)
            return results

    # Artifacts
    def save_artifact(self, artifact: dict):
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO artifacts (
                    id, workflow_id, task_id, filename, file_path, file_size, file_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.get("id", str(datetime.now().timestamp())),
                    artifact.get("workflow_id", ""),
                    artifact.get("task_id"),
                    artifact.get("filename", ""),
                    artifact.get("file_path", ""),
                    artifact.get("file_size", 0),
                    artifact.get("file_type", ""),
                    now
                )
            )
            conn.commit()

    def get_workflow_artifacts(self, workflow_id: str) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM artifacts WHERE workflow_id = ? ORDER BY created_at ASC", (workflow_id,))
            return [dict(r) for r in cursor.fetchall()]

    # Logs
    def add_log(self, workflow_id: str, level: str, message: str, task_id: Optional[str] = None, details: Optional[dict] = None):
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO execution_logs (workflow_id, task_id, level, message, details_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (workflow_id, task_id, level, message, json.dumps(details or {}), now)
            )
            conn.commit()

    def get_workflow_logs(self, workflow_id: str, limit: int = 100) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM execution_logs WHERE workflow_id = ? ORDER BY timestamp ASC LIMIT ?", (workflow_id, limit))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["details"] = json.loads(item["details_json"] or "{}")
                results.append(item)
            return results

    # Evaluations
    def save_evaluation(self, eval_record: dict):
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO evaluations (
                    id, suite_name, total_scenarios, passed_scenarios,
                    metrics_json, scenario_results_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eval_record["id"],
                    eval_record["suite_name"],
                    eval_record["total_scenarios"],
                    eval_record["passed_scenarios"],
                    json.dumps(eval_record["metrics"]),
                    json.dumps(eval_record["scenario_results"]),
                    now
                )
            )
            conn.commit()

    def list_evaluations(self, limit: int = 10) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM evaluations ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["metrics"] = json.loads(item["metrics_json"] or "{}")
                item["scenario_results"] = json.loads(item["scenario_results_json"] or "[]")
                results.append(item)
            return results

db = DatabaseManager()
