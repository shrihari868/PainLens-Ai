import streamlit as st
from datetime import datetime

from streamlit_webrtc import (
    webrtc_streamer,
    WebRtcMode,
    RTCConfiguration
)

import streamlit.components.v1 as components

from Modules.session_report import (
    build_session_summary,
    build_printable_html
)

from Modules.video_processor import VideoProcessor

from Modules.body_input import (
    initialize_database,
    render_body_viewer,
    save_observation,
    get_observations,
    save_patient,
    get_patients
)

from Modules.session_storage import (
    initialize_session_storage,
    save_monitoring_session
)

from Modules.guardian_observations import (
    initialize_guardian_storage,
    render_guardian_questionnaire
)

# New: combined Analytics dashboard
from Modules.analytics_dashboard import render_analytics_dashboard


# ==========================================
# 1. WEBRTC CONFIGURATION
# ==========================================

RTC_CONFIGURATION = RTCConfiguration(
    {
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {"urls": ["stun:stun1.google.com:19302"]},
        ]
    }
)


# ==========================================
# 2. PAGE CONFIGURATION AND INITIALIZATION
# ==========================================

st.set_page_config(
    page_title="PainLens AI",
    page_icon="🧠",
    layout="wide"
)

initialize_database()
initialize_session_storage()
initialize_guardian_storage()

if "selected_patient_id" not in st.session_state:
    st.session_state.selected_patient_id = None


# ==========================================
# 3. CUSTOM DESIGN
# ==========================================

st.markdown("""
<style>
.main-title {
    font-size: 44px;
    font-weight: 800;
    color: #2563EB;
}
.subtitle {
    font-size: 18px;
    color: #64748B;
}
div[data-testid="stMetric"] {
    background-color: rgba(128, 128, 128, 0.08);
    padding: 18px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 4. SIDEBAR NAVIGATION
# ==========================================

st.sidebar.title("🧠 PainLens AI")
st.sidebar.caption("AI-Assisted Behavioural Observation Platform")
st.sidebar.divider()

page = st.sidebar.radio(
    "NAVIGATION",
    [
        "Dashboard",
        "Guardian Observations",
        "Live Monitoring",
        "Body Map",
        "Analytics",
        "Patient History"
    ]
)

st.sidebar.divider()
st.sidebar.caption("Prototype Version 1.0")
st.sidebar.caption("Hackathon Project")


# ==========================================
# 5. DASHBOARD
# ==========================================

if page == "Dashboard":

    st.markdown(
        '<div class="main-title">PainLens AI</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="subtitle">Helping caregivers understand observable signs '
        'of discomfort in non-verbal children.</div>',
        unsafe_allow_html=True
    )

    st.divider()
    st.header("Welcome to PainLens AI")
    st.write("""
    PainLens AI is an AI-assisted behavioural observation
    platform designed to help caregivers identify and
    communicate possible signs of discomfort in
    non-verbal children.

    The platform combines:
    - Facial movement observations
    - Body posture and gesture observations
    - Caregiver-provided body location
    - Historical behavioural records
    - Personal baseline comparisons
    """)

    st.divider()
    st.header("👤 Patient Information")
    st.write(
        "Enter the patient's basic and medical information "
        "to create a patient profile."
    )

    with st.form("patient_registration_form"):
        st.subheader("Basic Information")
        col1, col2 = st.columns(2)

        with col1:
            patient_name = st.text_input(
                "Patient Name *",
                placeholder="Enter patient's full name"
            )
            patient_age = st.number_input(
                "Age *",
                min_value=0,
                max_value=120,
                value=0,
                step=1
            )

        with col2:
            patient_sex = st.selectbox(
                "Sex *",
                ["Select", "Male", "Female", "Other", "Prefer not to say"]
            )
            patient_blood_group = st.selectbox(
                "Blood Group *",
                [
                    "Select", "A+", "A-", "B+", "B-", "AB+", "AB-",
                    "O+", "O-", "Unknown"
                ]
            )

        st.divider()
        st.subheader("Medical Information")

        special_medical_condition = st.text_area(
            "Special Medical Condition",
            placeholder=(
                "For example: Autism, cerebral palsy, "
                "developmental condition, allergies, etc."
            ),
            height=100
        )
        current_medical_condition = st.text_area(
            "Current Medical Condition",
            placeholder=(
                "Describe any current illness, symptoms, "
                "injury, discomfort or other relevant condition..."
            ),
            height=100
        )

        st.caption("* Required fields")
        save_patient_button = st.form_submit_button(
            "💾 Save Patient Details",
            type="primary",
            use_container_width=True
        )

    if save_patient_button:
        if not patient_name.strip():
            st.error("Please enter the patient's name.")
        elif patient_sex == "Select":
            st.error("Please select the patient's sex.")
        elif patient_blood_group == "Select":
            st.error("Please select the patient's blood group.")
        else:
            try:
                patient_id = save_patient(
                    name=patient_name,
                    age=int(patient_age),
                    sex=patient_sex,
                    blood_group=patient_blood_group,
                    special_medical_condition=special_medical_condition,
                    current_medical_condition=current_medical_condition
                )

                st.session_state.selected_patient_id = patient_id
                st.session_state.dashboard_patient_selector = patient_id

                st.success("Patient information saved successfully!")
                st.info(f"Patient ID: {patient_id}")
            except Exception as error:
                st.error(f"Unable to save patient information: {error}")

    st.divider()
    st.subheader("👤 Select Active Patient")

    patients = get_patients()

    if patients:
        patient_lookup = {
            patient["id"]: patient
            for patient in patients
        }
        patient_ids = list(patient_lookup.keys())
        saved_id = st.session_state.selected_patient_id

        if saved_id not in patient_ids:
            saved_id = patient_ids[0]

        if (
            st.session_state.get("dashboard_patient_selector")
            not in patient_ids
        ):
            st.session_state.dashboard_patient_selector = saved_id

        active_patient_id = st.selectbox(
            "Choose the patient for observation",
            options=patient_ids,
            format_func=lambda pid: (
                f"{patient_lookup[pid]['name']} (ID: {pid})"
            ),
            key="dashboard_patient_selector"
        )

        st.session_state.selected_patient_id = active_patient_id
        active_patient = patient_lookup[active_patient_id]

        st.success(
            f"Active patient: {active_patient['name']} "
            f"| Patient ID: {active_patient_id}"
        )

        with st.expander("View Active Patient Information"):
            st.write("**Name:**", active_patient["name"])
            st.write("**Age:**", active_patient["age"])
            st.write("**Sex:**", active_patient["sex"])
            st.write("**Blood Group:**", active_patient["blood_group"])
            st.write(
                "**Special Medical Condition:**",
                active_patient["special_medical_condition"]
            )
            st.write(
                "**Current Medical Condition:**",
                active_patient["current_medical_condition"]
            )
    else:
        st.session_state.selected_patient_id = None
        st.warning(
            "Please register a patient before starting "
            "patient-specific observations."
        )

    st.divider()
    st.subheader("Monitoring Overview")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Monitoring Status", "Inactive")
    with col2:
        st.metric("Observations Today", "0")
    with col3:
        st.metric("Camera Status", "Disconnected")

    st.divider()
    st.subheader("Application Modules")
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.subheader("📹 Live Monitoring")
            st.write(
                "Observe facial movements, body posture "
                "and movement patterns through a webcam."
            )
        with st.container(border=True):
            st.subheader("🗺️ Body Map")
            st.write(
                "Record the body region where the child "
                "or caregiver reports discomfort."
            )

    with col2:
        with st.container(border=True):
            st.subheader("📊 Analytics")
            st.write(
                "Visualise behavioural changes and compare "
                "them with the child's personal baseline."
            )
        with st.container(border=True):
            st.subheader("📁 Patient History")
            st.write(
                "Review previously recorded observations "
                "and caregiver notes."
            )

    st.divider()
    st.info(
        "Medical disclaimer: PainLens AI is an experimental "
        "observation and communication tool. It does not "
        "diagnose pain or replace professional medical advice."
    )
    st.caption(
        "Last updated: " + datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    )


# ==========================================
# 6. GUARDIAN OBSERVATIONS
# ==========================================

elif page == "Guardian Observations":
    render_guardian_questionnaire()


# ==========================================
# 7. LIVE MONITORING
# ==========================================

elif page == "Live Monitoring":

    st.title("📹 PainLens AI - Live Monitoring")
    st.write(
        "Live observation of facial expressions, "
        "facial geometry and body movement."
    )
    st.divider()

    if "pain_session_processor" not in st.session_state:
        st.session_state.pain_session_processor = None
    if "pain_session_active" not in st.session_state:
        st.session_state.pain_session_active = False
    if "pain_completed_sessions" not in st.session_state:
        st.session_state.pain_completed_sessions = []
    if "pain_session_patient_id" not in st.session_state:
        st.session_state.pain_session_patient_id = None

    current_patient_id = st.session_state.get("selected_patient_id")
    current_patients = get_patients()

    current_patient = next(
        (
            patient for patient in current_patients
            if patient["id"] == current_patient_id
        ),
        None
    )

    if current_patient:
        st.success(
            f"Selected patient: {current_patient['name']} "
            f"| Patient ID: {current_patient_id}"
        )
    else:
        st.warning(
            "No active patient selected. Please register or "
            "select a patient from the Dashboard before "
            "starting a monitoring session."
        )

    video_col, observation_col = st.columns([1.35, 1], gap="large")

    with video_col:
        st.subheader("📷 Live Camera")
        st.info(
            "Start the camera first. Then use the session "
            "controls below to record numerical observations."
        )

        webrtc_ctx = webrtc_streamer(
            key="painlens-camera",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIGURATION,
            video_processor_factory=VideoProcessor,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True
        )

        current_processor = webrtc_ctx.video_processor
        if current_processor is not None:
            st.session_state.pain_session_processor = current_processor

        processor = (
            current_processor
            if current_processor is not None
            else st.session_state.pain_session_processor
        )

        camera_running = (
            webrtc_ctx.state.playing
            and current_processor is not None
        )

        st.divider()
        st.subheader("⏱️ Observation Session")
        control_col1, control_col2 = st.columns(2)

        with control_col1:
            start_clicked = st.button(
                "▶️ Start Session",
                type="primary",
                use_container_width=True,
                disabled=(
                    not camera_running
                    or st.session_state.pain_session_active
                    or current_patient is None
                ),
                key="painlens_start_session"
            )

        with control_col2:
            stop_clicked = st.button(
                "⏹️ Stop Session",
                use_container_width=True,
                disabled=(
                    not st.session_state.pain_session_active
                    or processor is None
                ),
                key="painlens_stop_session"
            )

        if start_clicked:
            selected_patient_id = st.session_state.get(
                "selected_patient_id"
            )

            if selected_patient_id is None:
                st.error(
                    "Please select a patient before starting "
                    "the monitoring session."
                )
            else:
                started = current_processor.start_session()

                if started:
                    st.session_state.pain_session_processor = current_processor
                    st.session_state.pain_session_patient_id = selected_patient_id
                    st.session_state.pain_session_active = True

                    st.success(
                        "Session started. Numerical observations "
                        "are now being collected."
                    )
                    st.info(
                        f"Session linked to Patient ID: {selected_patient_id}"
                    )
                else:
                    st.warning("A session is already active.")

        if stop_clicked:
            completed_session = processor.stop_session()

            if completed_session is not None:
                st.session_state.pain_completed_sessions.append(
                    completed_session
                )

                session_patient_id = (
                    st.session_state.pain_session_patient_id
                )
                st.session_state.pain_session_active = False

                try:
                    if session_patient_id is None:
                        raise ValueError(
                            "No Patient ID was captured for this session. "
                            "The session report is available, but it cannot "
                            "be saved as a patient-linked record."
                        )

                    saved = save_monitoring_session(
                        session=completed_session,
                        patient_id=session_patient_id
                    )

                    if saved:
                        st.success(
                            "Session stopped and permanently "
                            "saved to the database!"
                        )
                        st.success(
                            f"Linked Patient ID: {session_patient_id}"
                        )
                    else:
                        st.info(
                            "This session was already saved in the database. "
                            "No duplicate record was created."
                        )
                except Exception as error:
                    st.error(
                        "The session report is available in this browser "
                        "session, but permanent database saving failed."
                    )
                    st.error(f"Database error: {error}")

                st.session_state.pain_session_patient_id = None
            else:
                st.warning("No active session was found.")
                st.session_state.pain_session_active = False
                st.session_state.pain_session_patient_id = None

        if st.session_state.pain_session_active:
            st.success("Recording numerical observations...")
            st.caption(
                "Session Patient ID: "
                f"{st.session_state.pain_session_patient_id}"
            )
        elif not camera_running:
            st.caption(
                "Camera is not running. Start the camera to begin "
                "an observation session."
            )
        elif current_patient is None:
            st.caption(
                "Select a patient from the Dashboard before "
                "starting a session."
            )
        else:
            st.caption("Camera is running. Start a session when ready.")

    with observation_col:
        st.subheader("🧠 Live Observation Panel")

        def display_value(value, digits=2, suffix=""):
            if value is None:
                return "Collecting..."
            if isinstance(value, (int, float)):
                return f"{value:.{digits}f}{suffix}"
            return str(value)

        @st.fragment(run_every="1s")
        def render_live_observations():

            if (
                not webrtc_ctx.state.playing
                or webrtc_ctx.video_processor is None
            ):
                st.warning(
                    "Start the camera to view live observations."
                )
                return

            data = webrtc_ctx.video_processor.get_latest_data()
            metrics = data.get("metrics", {})
            observations = data.get("observations", [])

            st.markdown("**Detection Status**")
            status_col1, status_col2, status_col3 = st.columns(3)

            status_col1.metric(
                "Face",
                "Detected" if data["face_detected"] else "Not detected"
            )
            status_col2.metric(
                "Body",
                "Detected" if data["pose_detected"] else "Not detected"
            )
            status_col3.metric(
                "Hands",
                "Detected" if data["hands_detected"] else "Not detected"
            )

            st.divider()
            st.markdown("**👁️ Eye Observations**")
            eye_col1, eye_col2 = st.columns(2)

            eye_col1.metric(
                "Eye Aspect Ratio",
                display_value(metrics.get("eye_aspect_ratio"), 3)
            )

            blink_rate = metrics.get("blink_rate")
            eye_col2.metric(
                "Blink Rate",
                (
                    f"{blink_rate} blinks/min"
                    if blink_rate is not None
                    else "Baseline pending"
                )
            )

            eye_col1, eye_col2 = st.columns(2)
            eye_col1.metric(
                "Eye Status",
                metrics.get("eye_status", "Unavailable")
            )
            eye_col2.metric(
                "Eye Closure Duration",
                display_value(
                    metrics.get("eye_closure_duration"), 2, " sec"
                )
            )

            if blink_rate is None and data["face_detected"]:
                st.caption(
                    "Blink rate requires a complete 60-second "
                    "observation window."
                )

            st.divider()
            st.markdown("**👄 Mouth Opening Indicator**")
            mouth_col1, mouth_col2 = st.columns(2)

            mouth_col1.metric(
                "Mouth Aspect Ratio",
                display_value(metrics.get("mouth_aspect_ratio"), 3)
            )
            mouth_col2.metric(
                "Mouth Status",
                metrics.get("mouth_status", "Unavailable")
            )

            mouth_col1, mouth_col2 = st.columns(2)
            mouth_col1.metric(
                "Opening Duration",
                display_value(
                    metrics.get("mouth_open_duration"), 2, " sec"
                )
            )
            mouth_col2.metric(
                "Opening Events",
                str(metrics.get("mouth_open_frequency", 0))
            )

            if metrics.get("possible_sustained_mouth_opening"):
                st.warning("Sustained mouth opening observed.")

            st.divider()
            st.markdown("**📐 Eye-Nose-Mouth Geometry**")
            geometry_col1, geometry_col2 = st.columns(2)

            geometry_col1.metric(
                "Nose-to-Eye Ratio",
                display_value(metrics.get("nose_to_eye_ratio"), 3)
            )
            geometry_col2.metric(
                "Nose-to-Mouth Ratio",
                display_value(metrics.get("nose_to_mouth_ratio"), 3)
            )

            geometry_col1, geometry_col2 = st.columns(2)
            geometry_col1.metric(
                "Head Roll (2D Estimate)",
                display_value(
                    metrics.get("head_roll_degrees"), 2, "°"
                )
            )
            geometry_col2.metric(
                "Geometry Change",
                display_value(
                    metrics.get("facial_geometry_change"), 4
                )
            )

            st.divider()
            st.markdown("**🧍 Body Observations**")
            body_col1, body_col2 = st.columns(2)

            body_col1.metric(
                "Torso Inclination",
                display_value(
                    metrics.get("torso_inclination"), 2, "°"
                )
            )
            body_col2.metric(
                "Hand-to-Torso Distance",
                display_value(
                    metrics.get("hand_to_torso_distance"), 3
                )
            )

            body_col1, body_col2 = st.columns(2)
            body_col1.metric(
                "Hands Detected",
                str(metrics.get("hands_detected", 0))
            )

            tracking_quality = metrics.get("tracking_quality")
            body_col2.metric(
                "Body Tracking Quality",
                (
                    f"{tracking_quality * 100:.1f}%"
                    if tracking_quality is not None
                    else "Unavailable"
                )
            )

            st.divider()
            st.markdown("**📋 Recent Observations**")

            if observations:
                for observation in observations:
                    st.info(observation)
            else:
                st.caption(
                    "No new observation events at this moment."
                )

            if data.get("timestamp"):
                st.caption(
                    f"Last processed frame: {data['timestamp']}"
                )

        render_live_observations()

    st.divider()
    st.header("📄 Session Report")

    if st.session_state.pain_completed_sessions:
        completed_session = st.session_state.pain_completed_sessions[-1]
        report_summary = build_session_summary(completed_session)

        report_col1, report_col2, report_col3, report_col4 = st.columns(4)

        report_col1.metric(
            "Duration",
            f"{completed_session['duration_seconds']:.1f} sec"
        )
        report_col2.metric(
            "Recorded Samples",
            completed_session["sample_count"]
        )
        report_col3.metric(
            "Detected Events",
            report_summary["event_count"]
        )

        blink_count = report_summary["session_blink_count"]
        report_col4.metric(
            "Session Blinks",
            str(blink_count) if blink_count is not None else "Unavailable"
        )

        st.caption(
            f"Session ID: {completed_session['session_id']} | "
            f"Started: {completed_session['started_at']} | "
            f"Stopped: {completed_session['stopped_at']}"
        )

        st.subheader("Measurement Summary")
        if report_summary["measurements"]:
            st.dataframe(
                [
                    {
                        "Measurement": item["measurement"],
                        "Valid Samples": item["valid_samples"],
                        "Average": round(item["average"], 4),
                        "Minimum": round(item["minimum"], 4),
                        "Maximum": round(item["maximum"], 4)
                    }
                    for item in report_summary["measurements"]
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No valid numerical measurements were recorded.")

        st.subheader("Event Timeline")
        if completed_session["events"]:
            st.dataframe(
                [
                    {
                        "Timestamp": event["timestamp"],
                        "Elapsed Seconds": event["elapsed_seconds"],
                        "Event": event["event"]
                    }
                    for event in completed_session["events"]
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No events were recorded during this session.")

        st.subheader("Recorded Samples")
        if completed_session["samples"]:
            sample_rows = []

            for index, sample in enumerate(
                completed_session["samples"], start=1
            ):
                metrics = sample.get("metrics", {})
                sample_rows.append({
                    "Sample": index,
                    "Timestamp": sample["timestamp"],
                    "Elapsed Seconds": sample["elapsed_seconds"],
                    "EAR": metrics.get("eye_aspect_ratio"),
                    "Blink Rate": metrics.get("blink_rate"),
                    "Session Blink Count": metrics.get("session_blink_count"),
                    "Mouth Ratio": metrics.get("mouth_aspect_ratio"),
                    "Eye Status": metrics.get("eye_status"),
                    "Mouth Status": metrics.get("mouth_status"),
                    "Torso Inclination": metrics.get("torso_inclination"),
                    "Tracking Quality": metrics.get("tracking_quality")
                })

            st.dataframe(
                sample_rows,
                use_container_width=True,
                hide_index=True
            )

        st.subheader("🖨️ Printable Report")
        printable_html = build_printable_html(completed_session)

        components.html(
            printable_html,
            height=700,
            scrolling=True
        )

        st.download_button(
            "⬇️ Download Printable HTML Report",
            data=printable_html,
            file_name=(
                f"PainLens_Session_{completed_session['session_id']}.html"
            ),
            mime="text/html",
            use_container_width=True
        )

        if len(st.session_state.pain_completed_sessions) > 1:
            st.caption(
                f"{len(st.session_state.pain_completed_sessions)} "
                "completed sessions are retained in this browser "
                "session. The latest report is displayed above."
            )
    else:
        st.info(
            "No completed session report yet. Start the camera, "
            "begin a session, and stop it to generate your first report."
        )

    st.divider()
    st.caption(
        "PainLens AI is an experimental observation prototype. "
        "Facial and body measurements are not proof of pain and "
        "must not be used as a medical diagnosis. Only numerical "
        "observations and timestamps are recorded; webcam video is not saved."
    )


# ==========================================
# 8. BODY MAP - INTERACTIVE 3D INPUT
# ==========================================

elif page == "Body Map":

    st.title("🗺️ Interactive 3D Body Map")

    active_patient_id = st.session_state.get("selected_patient_id")
    patients = get_patients()

    active_patient = next(
        (
            patient for patient in patients
            if patient["id"] == active_patient_id
        ),
        None
    )

    if active_patient:
        st.success(
            f"Selected patient: {active_patient['name']} "
            f"| Patient ID: {active_patient_id}"
        )
    else:
        st.warning(
            "No patient selected. Please visit Dashboard and register "
            "or select a patient before saving a Body Map observation."
        )

    st.write(
        "Select the body region where the child communicates "
        "or the caregiver observes discomfort."
    )
    st.info(
        "Move your cursor over a body region to identify it. "
        "Click to select. You can select multiple regions."
    )

    st.divider()
    st.subheader("Select Body Regions")

    selection_data = render_body_viewer(
        height=720,
        key="painsense-body-viewer"
    )

    if not isinstance(selection_data, dict):
        selection_data = {}

    selected_regions = selection_data.get("selected_regions", [])
    body_view = selection_data.get("body_view", "Front")

    body_part_names = {
        "head": "Head",
        "neck": "Neck",
        "chest": "Chest",
        "abdomen": "Abdomen",
        "pelvis": "Pelvic Region",
        "upper_back": "Upper Back",
        "lower_back": "Lower Back",
        "left_upper_arm": "Left Upper Arm",
        "right_upper_arm": "Right Upper Arm",
        "left_forearm": "Left Forearm",
        "right_forearm": "Right Forearm",
        "left_hand": "Left Hand",
        "right_hand": "Right Hand",
        "left_thigh": "Left Thigh",
        "right_thigh": "Right Thigh",
        "left_knee": "Left Knee",
        "right_knee": "Right Knee",
        "left_lower_leg": "Left Lower Leg",
        "right_lower_leg": "Right Lower Leg",
        "left_foot": "Left Foot",
        "right_foot": "Right Foot"
    }

    st.divider()
    st.subheader("Your Selected Regions")

    if selected_regions:
        for region in selected_regions:
            region_name = body_part_names.get(region, region)
            st.success("✓ " + region_name)
    else:
        st.caption("No body regions selected yet.")

    st.divider()
    st.subheader("Observation Details")

    input_source = st.selectbox(
        "Who provided this information?",
        ["Child selection", "Caregiver observation", "Other"]
    )

    notes = st.text_area(
        "Additional observations (optional)",
        placeholder=(
            "Describe any additional information provided "
            "by the child or caregiver..."
        )
    )

    if st.button(
        "Save Body Observation",
        type="primary",
        disabled=(not selected_regions or active_patient is None)
    ):
        try:
            save_observation(
                selected_regions=selected_regions,
                body_view=body_view,
                input_source=input_source,
                notes=notes,
                patient_id=active_patient_id
            )

            st.success(
                f"Body observation successfully saved for "
                f"{active_patient['name']}!"
            )
            st.write(
                "**Selected regions:**",
                ", ".join(
                    body_part_names.get(region, region)
                    for region in selected_regions
                )
            )
            st.write("**Patient ID:**", active_patient_id)
            st.write("**Input source:**", input_source)
            st.write("**Body view:**", body_view)
        except Exception as error:
            st.error(f"Unable to save observation: {error}")

    st.divider()
    st.subheader("Recently Saved Observations")

    saved_records = get_observations()
    patient_names = {
        patient["id"]: patient["name"]
        for patient in patients
    }

    if saved_records:
        for record in saved_records[:10]:
            with st.container(border=True):
                st.write("**Observation ID:**", record["id"])
                record_patient_id = record.get("patient_id")

                if record_patient_id is not None:
                    record_patient_name = patient_names.get(
                        record_patient_id,
                        "Patient record unavailable"
                    )
                    st.write(
                        "**Patient:**",
                        f"{record_patient_name} (ID: {record_patient_id})"
                    )
                else:
                    st.caption(
                        "Historical observation — not linked to a patient."
                    )

                st.write(
                    "**Selected regions:**",
                    ", ".join(
                        body_part_names.get(region, region)
                        for region in record["selected_regions"]
                    )
                )
                st.write("**Input source:**", record["input_source"])
                st.write("**Body view:**", record["body_view"])
                st.write("**Date and time:**", record["created_at"])

                if record["notes"]:
                    st.write("**Notes:**", record["notes"])
    else:
        st.info("No body observations have been saved yet.")

    st.caption(
        "PainLens AI records communicated or caregiver-observed body "
        "locations. It does not independently diagnose pain."
    )


# ==========================================
# 9. ANALYTICS
# ==========================================

elif page == "Analytics":
    render_analytics_dashboard()


# ==========================================
# 10. PATIENT HISTORY
# ==========================================

elif page == "Patient History":

    st.title("📁 Patient History")
    st.write(
        "This module will maintain a record of caregiver observations."
    )
    st.divider()
    st.subheader("Observation Records")
    st.info(
        "No records available yet. Database integration "
        "will be implemented in the next stage."
    )


# ==========================================
# END OF APPLICATION
# ==========================================
