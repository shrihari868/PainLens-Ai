import streamlit as st
from datetime import datetime
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from Modules.video_processor import VideoProcessor

# Public STUN servers for WebRTC NAT traversal on cloud hosts
RTC_CONFIGURATION = RTCConfiguration(
    {
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {"urls": ["stun:stun1.l.google.com:19302"]},
        ]
    }
)

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="PainLens AI",
    page_icon="🧠",
    layout="wide"
)

# ==========================================
# 2. CUSTOM DESIGN
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
# 3. SIDEBAR NAVIGATION
# ==========================================

st.sidebar.title("🧠 PainLens AI")

st.sidebar.caption(
    "AI-Assisted Behavioural Observation Platform"
)

st.sidebar.divider()

page = st.sidebar.radio(
    "NAVIGATION",
    [
        "Dashboard",
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
# 4. DASHBOARD
# ==========================================

if page == "Dashboard":

    st.markdown(
        '<div class="main-title">PainLens AI</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'Helping caregivers understand observable signs '
        'of discomfort in non-verbal children.'
        '</div>',
        unsafe_allow_html=True
    )

    st.divider()

    st.header("Welcome to PainLens AI")

    st.write("""
    PainSense AI is an AI-assisted behavioural observation
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

    st.subheader("Monitoring Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Monitoring Status",
            "Inactive"
        )

    with col2:
        st.metric(
            "Observations Today",
            "0"
        )

    with col3:
        st.metric(
            "Camera Status",
            "Disconnected"
        )

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
        "Medical disclaimer: PainSense AI is an experimental "
        "observation and communication tool. It does not "
        "diagnose pain or replace professional medical advice."
    )

    st.caption(
        "Last updated: "
        + datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    )



# ==========================================
# 5. LIVE MONITORING
# ==========================================

elif page == "Live Monitoring":

    st.title("📹 PainLens AI - Live Monitoring")

    st.write(
        "Live video observation using OpenCV."
    )

    st.divider()

    st.subheader("Camera Feed")

    st.info(
        "Allow camera permission when your browser asks."
    )

    webrtc_streamer(
        key="painsense-camera",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=RTC_CONFIGURATION,
        video_processor_factory=VideoProcessor,
        media_stream_constraints={
            "video": True,
            "audio": False
        },
        async_processing=True
    )

    st.divider()

    st.subheader("Observation Modules")

    col1, col2 = st.columns(2)

    with col1:
        st.info("Facial landmark detection - Active in video pipeline")

    with col2:
        st.info("Body posture detection - Active in video pipeline")

    st.warning(
        "This prototype displays video only. "
        "It does not diagnose pain."
    )



# ==========================================
# 6. BODY MAP
# ==========================================

elif page == "Body Map":

    st.title("🗺️ Body Map")

    st.write(
        "Record the body region where discomfort "
        "is reported or suspected by the caregiver."
    )

    st.divider()

    body_region = st.selectbox(
        "Select body region",
        [
            "Not sure",
            "Head",
            "Neck",
            "Chest",
            "Abdomen",
            "Upper back",
            "Lower back",
            "Left arm",
            "Right arm",
            "Left leg",
            "Right leg",
            "Other"
        ]
    )

    observation_type = st.selectbox(
        "Who provided this information?",
        [
            "Caregiver observation",
            "Child's communication",
            "Other"
        ]
    )

    notes = st.text_area(
        "Additional observations",
        placeholder="Describe what you noticed..."
    )

    if st.button("Save Observation", type="primary"):

        st.success("Observation recorded in this session!")

        st.write("**Selected region:**", body_region)

        st.write("**Information source:**", observation_type)

        st.write("**Notes:**", notes)

        st.caption(
            "Note: Permanent database storage will be added later."
        )


# ==========================================
# 7. ANALYTICS
# ==========================================

elif page == "Analytics":

    st.title("📊 Behavioural Analytics")

    st.write(
        "This module will visualise observed behavioural "
        "changes over time."
    )

    st.divider()

    st.subheader("Planned observation metrics")

    col1, col2 = st.columns(2)

    with col1:
        st.info("Facial movement events")

        st.info("Eye closure duration")

    with col2:
        st.info("Body movement intensity")

        st.info("Posture changes")

    st.warning(
        "AI analysis and charts will be integrated in the "
        "next development stages."
    )


# ==========================================
# 8. PATIENT HISTORY
# ==========================================

elif page == "Patient History":

    st.title("📁 Patient History")

    st.write(
        "This module will maintain a record of "
        "caregiver observations."
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
