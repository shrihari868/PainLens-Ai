
import streamlit as st
from datetime import datetime

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="PainSense AI",
    page_icon="🧠",
    layout="wide"
)

# ==========================================
# 2. CUSTOM DESIGN
# ==========================================

st.markdown("""
<style>

.main-title {
    font-size: 42px;
    font-weight: 800;
    color: #2563EB;
}

.subtitle {
    font-size: 17px;
    color: #64748B;
}

</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. SIDEBAR NAVIGATION
# ==========================================

st.sidebar.title("🧠 PainSense AI")

st.sidebar.caption(
    "AI-Assisted Behavioural Observation Platform"
)

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

st.sidebar.info(
    "Prototype Version 1.0"
)

# ==========================================
# 4. DASHBOARD PAGE
# ==========================================

if page == "Dashboard":

    st.markdown(
        '<div class="main-title">PainSense AI</div>',
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

    st.header("Welcome to PainSense AI")

    st.write(
        """
        PainSense AI is an AI-assisted behavioural
        observation platform designed to help caregivers
        record and understand possible signs of discomfort.

        It combines facial movement analysis, body posture
        observations, caregiver inputs and historical records.
        """
    )

    # Dashboard metrics

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Monitoring Status",
            value="Inactive"
        )

    with col2:
        st.metric(
            label="Observations Today",
            value="0"
        )

    with col3:
        st.metric(
            label="Camera Status",
            value="Not Connected"
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
                "Record the body region where discomfort "
                "is reported by the child or caregiver."
            )

    with col2:

        with st.container(border=True):
            st.subheader("📊 Analytics")
            st.write(
                "Visualise observed behavioural changes "
                "and compare them with a personal baseline."
            )

        with st.container(border=True):
            st.subheader("📁 Patient History")
            st.write(
                "Review previously recorded observations "
                "and caregiver notes."
            )

    st.divider()

    st.info(
        "Important: This prototype supports observation "
        "and communication. It does not diagnose pain or "
        "replace professional medical assessment."
    )

    st.caption(
        "Last updated: "
        + datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    )

# ==========================================
# 5. LIVE MONITORING PAGE
# ==========================================

elif page == "Live Monitoring":

    st.title("📹 Live Monitoring")

    st.write(
        "This module will capture video and analyse "
        "observable facial and body movements."
    )

    st.warning(
        "Webcam integration is the next development step."
    )

# ==========================================
# 6. BODY MAP PAGE
# ==========================================

elif page == "Body Map":

    st.title("🗺️ Body Map")

    st.write(
        "Caregivers will be able to select the body "
        "region where discomfort is reported."
    )

    body_region = st.selectbox(
        "Select the body region",
        [
            "Not sure",
            "Head",
            "Neck",
            "Chest",
            "Abdomen",
            "Back",
            "Left arm",
            "Right arm",
            "Left leg",
            "Right leg",
            "Other"
        ]
    )

    notes = st.text_area(
        "Additional observations",
        placeholder="Describe what you observed..."
    )

    if st.button("Save observation"):

        st.success(
            f"Selected region: {body_region}"
        )

        st.write("Caregiver notes:", notes)

# ==========================================
# 7. ANALYTICS PAGE
# ==========================================

elif page == "Analytics":

    st.title("📊 Behavioural Analytics")

    st.write(
        "This page will display trends in observed "
        "facial movements and body movements."
    )

    st.info(
        "Charts and baseline comparisons will be "
        "added after computer vision integration."
    )

# ==========================================
# 8. PATIENT HISTORY PAGE
# ==========================================

elif page == "Patient History":

    st.title("📁 Patient History")

    st.write(
        "Previously recorded observations will appear here."
    )

    st.info(
        "Database integration will be implemented later."
    )
