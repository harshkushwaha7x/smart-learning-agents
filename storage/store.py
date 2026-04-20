"""Storage layer for persisting RunArtifacts in SQLite."""

import json
import sqlite3
from pathlib import Path
from typing import Optional, List

from schemas.models import RunArtifact


class ArtifactStore:

    def __init__(self, db_path: str = "artifacts.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS run_artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT UNIQUE NOT NULL,
                user_id TEXT,
                input_grade INTEGER NOT NULL,
                input_topic TEXT NOT NULL,
                final_status TEXT NOT NULL,
                artifact_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_run_id ON run_artifacts(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON run_artifacts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON run_artifacts(created_at)")

        conn.commit()
        conn.close()

    def store(self, artifact: RunArtifact) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        artifact_json = artifact.model_dump_json()

        try:
            cursor.execute("""
                INSERT INTO run_artifacts 
                (run_id, user_id, input_grade, input_topic, final_status, artifact_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                artifact.run_id,
                artifact.user_id,
                artifact.input.grade,
                artifact.input.topic,
                artifact.final.status.value,
                artifact_json,
            ))
            conn.commit()
        finally:
            conn.close()

    def get_by_run_id(self, run_id: str) -> Optional[RunArtifact]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT artifact_json FROM run_artifacts WHERE run_id = ?",
                (run_id,)
            )
            row = cursor.fetchone()
            if row:
                artifact_data = json.loads(row[0])
                return RunArtifact(**artifact_data)
            return None
        finally:
            conn.close()

    def get_by_user_id(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[RunArtifact]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """SELECT artifact_json FROM run_artifacts 
                   WHERE user_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ? OFFSET ?""",
                (user_id, limit, offset)
            )
            rows = cursor.fetchall()
            return [RunArtifact(**json.loads(row[0])) for row in rows]
        finally:
            conn.close()

    def list_all(self, limit: int = 100, offset: int = 0) -> List[RunArtifact]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """SELECT artifact_json FROM run_artifacts 
                   ORDER BY created_at DESC 
                   LIMIT ? OFFSET ?""",
                (limit, offset)
            )
            rows = cursor.fetchall()
            return [RunArtifact(**json.loads(row[0])) for row in rows]
        finally:
            conn.close()

    def count_by_user(self, user_id: str) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT COUNT(*) FROM run_artifacts WHERE user_id = ?",
                (user_id,)
            )
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def count_total(self) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM run_artifacts")
            return cursor.fetchone()[0]
        finally:
            conn.close()
