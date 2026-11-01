import sqlite3
import json
from pathlib import Path
from datetime import datetime

import streamlit as st


# ==========================================
# 1. DATABASE CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_PATH = (
    BASE_DIR
    / "Database"
    / "body_observations.db"
)


# ==========================================
# 2. DATABASE CONNECTION
# ==========================================

def get_connection():

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=30
    )

    connection.row_factory = sqlite3.Row

    return connection


# ==========================================
# 3. INITIALIZE GUARDIAN STORAGE
# ==========================================

def initialize_guardian_storage():

    """
    Creates the guardian_observations table if it
    does not already exist.

    Also adds missing questionnaire columns safely
    if an earlier version of the table exists.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guardian_observations (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                patient_id INTEGER NOT NULL,

                observed_behaviour TEXT,

                first_noticed TEXT,

                frequency TEXT,

                duration TEXT,

                triggers TEXT,

                different_from_usual TEXT,

                daily_changes TEXT,

                created_at TEXT,

                FOREIGN KEY (patient_id)
                REFERENCES patients(id)

            )
        """)

        # ----------------------------------
        # Check existing table columns
        # ----------------------------------

        cursor.execute("""
            PRAGMA table_info(guardian_observations)
        """)

        existing_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        # ----------------------------------
        # Safely add missing columns
        # ----------------------------------

        required_columns = {

            "patient_id": "INTEGER",

            "observed_behaviour": "TEXT",

            "first_noticed": "TEXT",

            "frequency": "TEXT",

            "duration": "TEXT",

            "triggers": "TEXT",

            "different_from_usual": "TEXT",

            "daily_changes": "TEXT",

            "created_at": "TEXT"
        }

        for column_name, column_type in required_columns.items():

            if column_name not in existing_columns:

                cursor.execute(
                    f"""
                    ALTER TABLE guardian_observations
                    ADD COLUMN {column_name} {column_type}
                    """
                )

        # ----------------------------------
        # Index for patient-specific history
        # ----------------------------------

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_guardian_patient_id
            ON guardian_observations(patient_id)
        """)

        connection.commit()

    finally:

        connection.close()


# ==========================================
# 4. SAVE GUARDIAN OBSERVATION
# ==========================================

def save_guardian_observation(
    patient_id,
    observed_behaviour=None,
    first_noticed=None,
    frequency=None,
    duration=None,
    triggers=None,
    different_from_usual=None,
    daily_changes=None
):

    """
    Saves one guardian questionnaire submission.

    Multiple submissions are allowed for the same
    patient. Each submission receives its own
    timestamp.
    """

    # ----------------------------------
    # Validate patient ID
    # ----------------------------------

    if patient_id is None:

        raise ValueError(
            "A valid Patient ID is required."
        )

    # ----------------------------------
    # Validate actual answers
    # ----------------------------------

    text_answers = [

        observed_behaviour,

        first_noticed,

        frequency,

        duration,

        triggers,

        different_from_usual
    ]

    has_text_answer = any(
        answer is not None
        and str(answer).strip() != ""
        for answer in text_answers
    )

    has_activity_answer = bool(
        daily_changes
    )

    if not has_text_answer and not has_activity_answer:

        raise ValueError(
            "Please answer at least one question "
            "before submitting."
        )

    # ----------------------------------
    # Clean daily activity selections
    # ----------------------------------

    cleaned_daily_changes = []

    if daily_changes:

        exclusive_options = [
            "No changes noticed",
            "Not sure"
        ]

        if "No changes noticed" in daily_changes:

            cleaned_daily_changes = [
                "No changes noticed"
            ]

        elif "Not sure" in daily_changes:

            cleaned_daily_changes = [
                "Not sure"
            ]

        else:

            cleaned_daily_changes = [
                str(item).strip()
                for item in daily_changes
                if str(item).strip()
                and item not in exclusive_options
            ]

    daily_changes_json = json.dumps(
        cleaned_daily_changes
    )

    # ----------------------------------
    # Timestamp
    # ----------------------------------

    created_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    connection = get_connection()

    try:

        cursor = connection.cursor()

        # ----------------------------------
        # Verify patient exists
        # ----------------------------------

        cursor.execute(
            """
            SELECT id
            FROM patients
            WHERE id = ?
            """,
            (patient_id,)
        )

        patient = cursor.fetchone()

        if patient is None:

            raise ValueError(
                "The selected patient does not exist "
                "in the patient database."
            )

        # ----------------------------------
        # Insert questionnaire submission
        # ----------------------------------

        cursor.execute(
            """
            INSERT INTO guardian_observations (

                patient_id,

                observed_behaviour,

                first_noticed,

                frequency,

                duration,

                triggers,

                different_from_usual,

                daily_changes,

                created_at

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,

            (

                patient_id,

                observed_behaviour,

                first_noticed,

                frequency,

                duration,

                triggers,

                different_from_usual,

                daily_changes_json,

                created_at

            )
        )

        observation_id = cursor.lastrowid

        connection.commit()

        return observation_id

    finally:

        connection.close()


# ==========================================
# 5. RETRIEVE GUARDIAN OBSERVATIONS
# ==========================================

def get_guardian_observations(patient_id=None):

    """
    Retrieves guardian submissions.

    If patient_id is supplied, only submissions
    belonging to that patient are returned.

    Results are ordered newest first.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        if patient_id is not None:

            cursor.execute(
                """
                SELECT *
                FROM guardian_observations
                WHERE patient_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                (patient_id,)
            )

        else:

            cursor.execute(
                """
                SELECT *
                FROM guardian_observations
                ORDER BY created_at DESC, id DESC
                """
            )

        records = cursor.fetchall()

        results = []

        for record in records:

            item = dict(record)

            # Decode daily activity selections
            raw_changes = item.get("daily_changes")

            try:

                item["daily_changes"] = (
                    json.loads(raw_changes)
                    if raw_changes
                    else []
                )

            except (json.JSONDecodeError, TypeError):

                item["daily_changes"] = []

            results.append(item)

        return results

    finally:

        connection.close()


# ==========================================
# 6. DISPLAY GUARDIAN OBSERVATION HISTORY
# ==========================================

def render_guardian_history(patient_id):

    st.subheader("📚 Previous Guardian Submissions")

    records = get_guardian_observations(patient_id)

    if not records:

        st.info(
            "No guardian observations have been submitted "
            "for this patient yet."
        )

        return

    st.caption(
        f"{len(records)} submission(s) found for this patient."
    )

    question_labels = {

        "observed_behaviour":
            "1. Unusual behaviour noticed",

        "first_noticed":
            "2. When it was first noticed",

        "frequency":
            "3. Frequency",

        "duration":
            "4. Usual duration",

        "triggers":
            "5. Possible triggers or worsening factors",

        "different_from_usual":
            "6. Different from usual behaviour",

        "daily_changes":
            "7. Changes in daily activities"
    }

    for record in records:

        with st.expander(
            f"Submission #{record['id']} — "
            f"{record.get('created_at') or 'Date unavailable'}"
        ):

            for field, label in question_labels.items():

                value = record.get(field)

                if field == "daily_changes":

                    if value:

                        display_value = ", ".join(value)

                    else:

                        display_value = "Not answered"

                else:

                    display_value = (
                        str(value).strip()
                        if value is not None
                        and str(value).strip()
                        else "Not answered"
                    )

                st.write(
                    f"**{label}:** {display_value}"
                )


# ==========================================
# 7. GUARDIAN QUESTIONNAIRE PAGE
# ==========================================

def render_guardian_questionnaire():

    st.title("👨‍👩‍👧 Guardian Observations")

    st.write(
        """
        This section allows parents or guardians to
        provide information about behavioural changes
        they have noticed in the child.

        These observations are saved separately from
        Live Monitoring and are permanently linked
        to the selected patient.
        """
    )

    st.divider()

    # ----------------------------------
    # GET REGISTERED PATIENTS
    # ----------------------------------

    from Modules.body_input import get_patients

    patients = get_patients()

    if not patients:

        st.warning(
            "No patients have been registered yet. "
            "Please register a patient from the Dashboard "
            "before submitting guardian observations."
        )

        return

    patient_lookup = {
        patient["id"]: patient
        for patient in patients
    }

    patient_ids = list(patient_lookup.keys())

    # ----------------------------------
    # PATIENT SELECTION
    # ----------------------------------

    st.subheader("👤 Select Patient")

    saved_patient_id = st.session_state.get(
        "selected_patient_id"
    )

    if saved_patient_id not in patient_ids:

        saved_patient_id = patient_ids[0]

    if (
        st.session_state.get("guardian_patient_selector")
        not in patient_ids
    ):

        st.session_state.guardian_patient_selector = (
            saved_patient_id
        )

    selected_patient_id = st.selectbox(

        "Choose the patient for this questionnaire",

        options=patient_ids,

        format_func=lambda pid: (
            f"{patient_lookup[pid]['name']} "
            f"(ID: {pid})"
        ),

        key="guardian_patient_selector"

    )

    # Synchronize selected patient across application pages
    st.session_state.selected_patient_id = selected_patient_id

    selected_patient = patient_lookup[selected_patient_id]

    st.success(
        f"Selected patient: {selected_patient['name']} "
        f"| Patient ID: {selected_patient_id}"
    )

    with st.expander("View Patient Information"):

        st.write(
            "**Age:**",
            selected_patient.get("age", "Not available")
        )

        st.write(
            "**Sex:**",
            selected_patient.get("sex", "Not available")
        )

        st.write(
            "**Blood Group:**",
            selected_patient.get("blood_group", "Not available")
        )

    st.divider()

    # ----------------------------------
    # QUESTIONNAIRE INTRODUCTION
    # ----------------------------------

    st.subheader("📝 Guardian Questionnaire")

    st.caption(
        "Please answer based on what you have personally "
        "noticed. You may leave questions unanswered if "
        "you are unsure."
    )

    # ----------------------------------
    # QUESTIONNAIRE FORM
    # ----------------------------------

    with st.form("guardian_observation_form"):

        # ----------------------------------
        # QUESTION 1
        # ----------------------------------

        st.markdown(
            "**1. What unusual behaviour have you noticed?**"
        )

        observed_behaviour = st.text_area(

            "Describe the behaviour",

            placeholder=(
                "For example: unusual crying, facial "
                "expressions, restlessness, withdrawal, "
                "repeated gestures, etc."
            ),

            height=100,

            key="guardian_observed_behaviour"

        )

        st.divider()

        # ----------------------------------
        # QUESTION 2
        # ----------------------------------

        st.markdown(
            "**2. When did you first notice it?**"
        )

        first_noticed = st.selectbox(

            "Approximate time",

            options=[
                "Not answered",
                "Today",
                "Within the last few days",
                "Within the last week",
                "Within the last month",
                "Several months ago",
                "More than a year ago",
                "Not sure"
            ],

            key="guardian_first_noticed"

        )

        st.divider()

        # ----------------------------------
        # QUESTION 3
        # ----------------------------------

        st.markdown(
            "**3. How frequently does it occur?**"
        )

        frequency = st.selectbox(

            "Frequency",

            options=[
                "Not answered",
                "Rarely",
                "Once in a while",
                "Several times a week",
                "Daily",
                "Several times a day",
                "Almost continuously",
                "Not sure"
            ],

            key="guardian_frequency"

        )

        st.divider()

        # ----------------------------------
        # QUESTION 4
        # ----------------------------------

        st.markdown(
            "**4. How long does it usually last?**"
        )

        duration = st.selectbox(

            "Approximate duration",

            options=[
                "Not answered",
                "A few seconds",
                "Less than 5 minutes",
                "5–15 minutes",
                "15–30 minutes",
                "30–60 minutes",
                "More than an hour",
                "Varies",
                "Not sure"
            ],

            key="guardian_duration"

        )

        st.divider()

        # ----------------------------------
        # QUESTION 5
        # ----------------------------------

        st.markdown(
            "**5. Does anything appear to trigger "
            "or worsen it?**"
        )

        triggers = st.text_area(

            "Possible triggers",

            placeholder=(
                "For example: movement, particular activities, "
                "sounds, touch, eating, changes in routine, "
                "or any other situation..."
            ),

            height=100,

            key="guardian_triggers"

        )

        st.divider()

        # ----------------------------------
        # QUESTION 6
        # ----------------------------------

        st.markdown(
            "**6. Does the child behave differently "
            "from their usual behaviour?**"
        )

        different_from_usual = st.selectbox(

            "Your observation",

            options=[
                "Not answered",
                "Yes",
                "No",
                "Not sure"
            ],

            key="guardian_different_from_usual"

        )

        st.divider()

        # ----------------------------------
        # QUESTION 7
        # ----------------------------------

        st.markdown(
            "**7. Have you noticed changes in sleep, "
            "appetite, movement, or daily activities?**"
        )

        daily_changes = st.multiselect(

            "Select all applicable observations",

            options=[
                "Changes in sleep",
                "Changes in appetite",
                "Changes in movement",
                "Changes in daily activities",
                "No changes noticed",
                "Not sure"
            ],

            key="guardian_daily_changes"

        )

        st.caption(
            "If you select 'No changes noticed' or 'Not sure', "
            "other selections will be excluded when saving."
        )

        st.divider()

        # ----------------------------------
        # SUBMIT
        # ----------------------------------

        submit_guardian_form = st.form_submit_button(

            "💾 Save Guardian Observations",

            type="primary",

            use_container_width=True

        )

    # ----------------------------------
    # SAVE SUBMISSION
    # ----------------------------------

    if submit_guardian_form:

        try:

            observation_id = save_guardian_observation(

                patient_id=selected_patient_id,

                observed_behaviour=(
                    observed_behaviour.strip()
                    or None
                ),

                first_noticed=(
                    first_noticed
                    if first_noticed != "Not answered"
                    else None
                ),

                frequency=(
                    frequency
                    if frequency != "Not answered"
                    else None
                ),

                duration=(
                    duration
                    if duration != "Not answered"
                    else None
                ),

                triggers=(
                    triggers.strip()
                    or None
                ),

                different_from_usual=(
                    different_from_usual
                    if different_from_usual != "Not answered"
                    else None
                ),

                daily_changes=daily_changes

            )

            st.success(
                "Guardian observations saved successfully!"
            )

            st.info(
                f"Submission ID: {observation_id}"
            )

            st.info(
                f"Patient ID: {selected_patient_id}"
            )

            st.rerun()

        except Exception as error:

            st.error(
                f"Unable to save guardian observations: {error}"
            )

    # ----------------------------------
    # PREVIOUS SUBMISSIONS
    # ----------------------------------

    st.divider()

    render_guardian_history(selected_patient_id)

    # ----------------------------------
    # DISCLAIMER
    # ----------------------------------

    st.divider()

    st.caption(
        "Guardian observations are personal reports of "
        "behaviour and daily activities. They are not a "
        "medical diagnosis or a confirmed measurement of pain."
    )