
from pathlib import Path
import sqlite3
import json
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components


# ==========================================
# 1. PROJECT PATHS
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

COMPONENT_PATH = (
    PROJECT_ROOT / "components" / "body_viewer"
)

DATABASE_FOLDER = PROJECT_ROOT / "Database"

DATABASE_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

DATABASE_PATH = (
    DATABASE_FOLDER / "body_observations.db"
)


# ==========================================
# 2. REGISTER THE 3D VIEWER
# ==========================================

body_viewer_component = components.declare_component(
    "painsense_body_viewer",
    path=str(COMPONENT_PATH)
)


def render_body_viewer(height=650, key="body-viewer"):

    return body_viewer_component(
        height=height,
        key=key,
        default=None
    )


# ==========================================
# 3. INITIALISE SQLITE DATABASE
# ==========================================

def initialize_database():

    connection = sqlite3.connect(DATABASE_PATH)

    try:

        cursor = connection.cursor()

        # Patient Information table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                age INTEGER NOT NULL,

                sex TEXT NOT NULL,

                blood_group TEXT NOT NULL,

                special_medical_condition TEXT,

                current_medical_condition TEXT,

                created_at TEXT NOT NULL

            )
        """)

        # Existing Body Map observations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS body_observations (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                selected_regions TEXT NOT NULL,

                body_view TEXT NOT NULL,

                input_source TEXT NOT NULL,

                notes TEXT,

                created_at TEXT NOT NULL

            )
        """)

        # ------------------------------------------
        # SAFE DATABASE MIGRATION
        # Add patient_id without deleting old data.
        # ------------------------------------------

        cursor.execute("""
            PRAGMA table_info(body_observations)
        """)

        columns = [
    column[1]
    for column in cursor.fetchall()
]

        if "patient_id" not in columns:

            cursor.execute("""
                ALTER TABLE body_observations
                ADD COLUMN patient_id INTEGER
            """)

        connection.commit()

    finally:
        connection.close()


# ==========================================
# 4. SAVE PATIENT INFORMATION
# ==========================================

def save_patient(
    name,
    age,
    sex,
    blood_group,
    special_medical_condition="",
    current_medical_condition=""
):

    name = name.strip()

    if not name:
        raise ValueError("Patient name is required.")

    if age < 0 or age > 120:
        raise ValueError("Please enter a valid age.")

    timestamp = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    connection = sqlite3.connect(DATABASE_PATH)

    try:

        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO patients (
                name,
                age,
                sex,
                blood_group,
                special_medical_condition,
                current_medical_condition,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            age,
            sex,
            blood_group,
            special_medical_condition.strip(),
            current_medical_condition.strip(),
            timestamp
        ))

        patient_id = cursor.lastrowid

        connection.commit()

        return patient_id

    finally:
        connection.close()


# ==========================================
# 5. RETRIEVE SAVED PATIENTS
# ==========================================

def get_patients():

    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM patients
            ORDER BY id DESC
        """)

        records = cursor.fetchall()

        return [dict(record) for record in records]

    finally:
        connection.close()


# ==========================================
# 6. SAVE BODY OBSERVATION
# ==========================================

def save_observation(
    selected_regions,
    body_view,
    input_source,
    notes="",
    patient_id=None
):

    if not selected_regions:
        raise ValueError("Select at least one body region.")

    timestamp = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    regions_json = json.dumps(selected_regions)

    connection = sqlite3.connect(DATABASE_PATH)

    try:

        cursor = connection.cursor()

        # Validate patient ID when supplied
        if patient_id is not None:

            cursor.execute("""
                SELECT id
                FROM patients
                WHERE id = ?
            """, (patient_id,))

            if cursor.fetchone() is None:
                raise ValueError(
                    "The selected patient does not exist."
                )

        cursor.execute("""
            INSERT INTO body_observations (
                selected_regions,
                body_view,
                input_source,
                notes,
                created_at,
                patient_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            regions_json,
            body_view,
            input_source,
            notes,
            timestamp,
            patient_id
        ))

        connection.commit()

    finally:
        connection.close()


# ==========================================
# 7. RETRIEVE SAVED OBSERVATIONS
# ==========================================

def get_observations(patient_id=None):

    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    try:

        cursor = connection.cursor()

        if patient_id is None:

            # Preserve old behaviour:
            # retrieve all observations.

            cursor.execute("""
                SELECT *
                FROM body_observations
                ORDER BY id DESC
            """)

        else:

            # Retrieve observations for one patient.

            cursor.execute("""
                SELECT *
                FROM body_observations
                WHERE patient_id = ?
                ORDER BY id DESC
            """, (patient_id,))

        records = cursor.fetchall()

        observations = []

        for record in records:

            item = dict(record)

            item["selected_regions"] = json.loads(
                item["selected_regions"]
            )

            observations.append(item)

        return observations

    finally:
        connection.close()
