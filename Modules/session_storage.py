
from pathlib import Path
import sqlite3
import json
from datetime import datetime


# ==========================================
# 1. DATABASE CONFIGURATION
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_PATH = (
    PROJECT_ROOT
    / "Database"
    / "body_observations.db"
)


# ==========================================
# 2. JSON SERIALIZATION SUPPORT
# ==========================================

def _json_default(value):

    # Support datetime objects if present.
    if isinstance(value, datetime):
        return value.isoformat()

    # Support NumPy scalar values if present.
    if hasattr(value, "item"):
        return value.item()

    raise TypeError(
        f"Object of type {type(value).__name__} "
        "is not JSON serializable."
    )


# ==========================================
# 3. INITIALIZE SESSION STORAGE
# ==========================================

def initialize_session_storage():

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(DATABASE_PATH)

    try:

        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_sessions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                patient_id INTEGER NOT NULL,

                session_id TEXT NOT NULL UNIQUE,

                started_at TEXT,

                stopped_at TEXT,

                duration_seconds REAL,

                sample_count INTEGER,

                session_data TEXT NOT NULL,

                created_at TEXT NOT NULL,

                FOREIGN KEY (patient_id)
                REFERENCES patients(id)

            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_monitoring_sessions_patient
            ON monitoring_sessions(patient_id)
        """)

        connection.commit()

    finally:
        connection.close()


# ==========================================
# 4. SAVE COMPLETED MONITORING SESSION
# ==========================================

def save_monitoring_session(session, patient_id):

    if not isinstance(session, dict):
        raise ValueError(
            "Invalid monitoring session data."
        )

    if patient_id is None:
        raise ValueError(
            "A patient must be selected before "
            "saving a monitoring session."
        )

    try:
        patient_id = int(patient_id)
    except (TypeError, ValueError):
        raise ValueError("Invalid Patient ID.")

    if patient_id <= 0:
        raise ValueError("Invalid Patient ID.")

    session_id = session.get("session_id")

    if not session_id:
        raise ValueError(
            "The monitoring session has no Session ID."
        )

    # Convert the complete session into JSON.
    session_json = json.dumps(
        session,
        default=_json_default,
        ensure_ascii=False,
        allow_nan=False
    )

    timestamp = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    connection = sqlite3.connect(DATABASE_PATH)

    try:

        cursor = connection.cursor()

        # Confirm that the patient exists.
        cursor.execute("""
            SELECT id
            FROM patients
            WHERE id = ?
        """, (patient_id,))

        if cursor.fetchone() is None:
            raise ValueError(
                "The selected patient does not exist."
            )

        # Prevent duplicate session records.
        cursor.execute("""
            SELECT id, patient_id
            FROM monitoring_sessions
            WHERE session_id = ?
        """, (session_id,))

        existing_record = cursor.fetchone()

        if existing_record is not None:

            existing_patient_id = existing_record[1]

            if existing_patient_id != patient_id:
                raise ValueError(
                    "This session ID is already linked "
                    "to a different patient."
                )

            # Already saved for the same patient.
            return False

        cursor.execute("""
            INSERT INTO monitoring_sessions (

                patient_id,
                session_id,
                started_at,
                stopped_at,
                duration_seconds,
                sample_count,
                session_data,
                created_at

            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            patient_id,
            session_id,
            session.get("started_at"),
            session.get("stopped_at"),
            session.get("duration_seconds"),
            session.get("sample_count"),
            session_json,
            timestamp

        ))

        connection.commit()

        return True

    finally:
        connection.close()


# ==========================================
# 5. RETRIEVE MONITORING SESSIONS
# ==========================================

def get_monitoring_sessions(patient_id=None):

    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    try:

        cursor = connection.cursor()

        if patient_id is None:

            cursor.execute("""
                SELECT *
                FROM monitoring_sessions
                ORDER BY id DESC
            """)

        else:

            cursor.execute("""
                SELECT *
                FROM monitoring_sessions
                WHERE patient_id = ?
                ORDER BY id DESC
            """, (int(patient_id),))

        records = cursor.fetchall()

        sessions = []

        for record in records:

            item = dict(record)

            item["session_data"] = json.loads(
                item["session_data"]
            )

            sessions.append(item)

        return sessions

    finally:
        connection.close()
