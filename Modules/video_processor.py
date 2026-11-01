
import cv2
import av
import threading
import time
import uuid
import copy

from datetime import datetime

from streamlit_webrtc import VideoProcessorBase

from Modules.face_analyser import analyze_face
from Modules.pose_analyser import analyze_pose
from Modules.hand_analyser import analyze_hands
from Modules.feature_extractor import extract_features
from Modules.observation_engine import ObservationEngine


class VideoProcessor(VideoProcessorBase):

    def __init__(self):

        self.engine = ObservationEngine()
        self.lock = threading.Lock()

        # ==========================================
        # LATEST LIVE OBSERVATION DATA
        # ==========================================

        self._latest_data = {
            "face_detected": False,
            "pose_detected": False,
            "hands_detected": False,
            "observations": [],
            "metrics": {},
            "timestamp": None
        }

        # ==========================================
        # SESSION RECORDING STATE
        # ==========================================

        # Only numerical observations, timestamps
        # and events are stored.
        # No webcam video frames are saved.

        self._session_active = False

        self._session_id = None
        self._session_started_at = None
        self._session_started_monotonic = None

        self._last_sample_monotonic = None

        self._session_samples = []
        self._session_events = []

        self._session_blink_baseline = 0

        # Used to detect changes in facial observations.
        self._previous_eye_status = None
        self._previous_mouth_status = None

        # Prevents the same observation event from
        # being recorded on every consecutive frame.
        self._last_observation_event = {}

    # ==========================================
    # 1. GET LATEST LIVE DATA
    # ==========================================

    def get_latest_data(self):
        """
        Safely return the latest live observations
        to the Streamlit interface.
        """

        with self.lock:
            return copy.deepcopy(self._latest_data)

    # ==========================================
    # 2. START SESSION
    # ==========================================

    def start_session(self):
        """
        Start a fresh numerical observation session.

        Returns:
            True  - session successfully started
            False - a session is already active
        """

        with self.lock:

            if self._session_active:
                return False

            now = datetime.now()
            monotonic_now = time.monotonic()

            # Capture the blink count at session start.
            # This allows us to calculate session-specific
            # blink counts instead of lifetime counts.

            latest_metrics = self._latest_data.get(
                "metrics", {}
            )

            blink_baseline = latest_metrics.get(
                "blink_count", 0
            )

            if (
                not isinstance(blink_baseline, (int, float))
                or isinstance(blink_baseline, bool)
            ):
                blink_baseline = 0

            # Generate a unique session ID.
            self._session_id = str(uuid.uuid4())[:8]

            self._session_started_at = (
                now.isoformat(timespec="seconds")
            )

            self._session_started_monotonic = monotonic_now

            self._last_sample_monotonic = None

            # Start with empty session records.
            self._session_samples = []
            self._session_events = []

            self._session_blink_baseline = blink_baseline

            # Reset event transition tracking.
            self._previous_eye_status = None
            self._previous_mouth_status = None

            self._last_observation_event = {}

            self._session_active = True

            return True

    # ==========================================
    # 3. STOP SESSION
    # ==========================================

    def stop_session(self):
        """
        Stop numerical recording and return
        the complete session report data.

        Webcam processing can continue independently.
        """

        with self.lock:

            if not self._session_active:
                return None

            stopped_at = datetime.now()

            duration = max(
                0.0,
                time.monotonic()
                - self._session_started_monotonic
            )

            self._session_active = False

            completed_session = {
                "session_id": self._session_id,

                "started_at": self._session_started_at,

                "stopped_at": stopped_at.isoformat(
                    timespec="seconds"
                ),

                "duration_seconds": round(duration, 2),

                "sample_count": len(
                    self._session_samples
                ),

                "samples": copy.deepcopy(
                    self._session_samples
                ),

                "events": copy.deepcopy(
                    self._session_events
                )
            }

            return completed_session

    # ==========================================
    # 4. GET CURRENT SESSION DATA
    # ==========================================

    def get_session_data(self):
        """
        Return the current session status and
        a safe copy of recorded numerical data.
        """

        with self.lock:

            duration = 0.0

            if (
                self._session_active
                and self._session_started_monotonic is not None
            ):

                duration = max(
                    0.0,
                    time.monotonic()
                    - self._session_started_monotonic
                )

            return {
                "active": self._session_active,

                "session_id": self._session_id,

                "started_at": self._session_started_at,

                "duration_seconds": round(duration, 2),

                "sample_count": len(
                    self._session_samples
                ),

                "samples": copy.deepcopy(
                    self._session_samples
                ),

                "events": copy.deepcopy(
                    self._session_events
                )
            }

    # ==========================================
    # 5. RECORD NUMERICAL SESSION DATA
    # ==========================================

    def _record_session_data(self, metrics, observations):
        """
        Record approximately one numerical sample
        per second.

        Also records:
        - Eye-status transitions
        - Mouth-status transitions
        - Observation-engine events

        No video frames are stored.
        """

        now_monotonic = time.monotonic()

        # Ensure metrics are dictionary-based.
        if not isinstance(metrics, dict):
            metrics = {}

        with self.lock:

            if not self._session_active:
                return

            elapsed = (
                now_monotonic
                - self._session_started_monotonic
            )

            # --------------------------------------
            # A. NUMERICAL SAMPLE RECORDING
            # --------------------------------------

            # Record approximately one sample per second.
            if (
                self._last_sample_monotonic is None
                or now_monotonic - self._last_sample_monotonic >= 1.0
            ):

                sample_metrics = copy.deepcopy(metrics)

                # Calculate session-specific blink count.
                blink_count = sample_metrics.get(
                    "blink_count", 0
                )

                if (
                    isinstance(blink_count, (int, float))
                    and not isinstance(blink_count, bool)
                ):

                    sample_metrics["session_blink_count"] = max(
                        0,
                        blink_count - self._session_blink_baseline
                    )

                else:

                    sample_metrics["session_blink_count"] = None

                sample = {
                    "timestamp": datetime.now().isoformat(
                        timespec="seconds"
                    ),

                    "elapsed_seconds": round(
                        elapsed, 2
                    ),

                    "metrics": sample_metrics
                }

                self._session_samples.append(sample)

                self._last_sample_monotonic = now_monotonic

            # --------------------------------------
            # B. EYE-STATUS TRANSITION EVENTS
            # --------------------------------------

            eye_status = metrics.get("eye_status")

            if (
                eye_status is not None
                and self._previous_eye_status is not None
                and eye_status != self._previous_eye_status
            ):

                self._session_events.append({

                    "timestamp": datetime.now().isoformat(
                        timespec="seconds"
                    ),

                    "elapsed_seconds": round(
                        elapsed, 2
                    ),

                    "event": (
                        f"Eye status changed: "
                        f"{self._previous_eye_status} → {eye_status}"
                    )

                })

            if eye_status is not None:
                self._previous_eye_status = eye_status

            # --------------------------------------
            # C. MOUTH-STATUS TRANSITION EVENTS
            # --------------------------------------

            mouth_status = metrics.get("mouth_status")

            if (
                mouth_status is not None
                and self._previous_mouth_status is not None
                and mouth_status != self._previous_mouth_status
            ):

                self._session_events.append({

                    "timestamp": datetime.now().isoformat(
                        timespec="seconds"
                    ),

                    "elapsed_seconds": round(
                        elapsed, 2
                    ),

                    "event": (
                        f"Mouth status changed: "
                        f"{self._previous_mouth_status} → {mouth_status}"
                    )

                })

            if mouth_status is not None:
                self._previous_mouth_status = mouth_status

            # --------------------------------------
            # D. OBSERVATION-ENGINE EVENTS
            # --------------------------------------

            for observation in observations or []:

                event_text = str(observation).strip()

                if not event_text:
                    continue

                previous_time = (
                    self._last_observation_event.get(
                        event_text
                    )
                )

                # Avoid recording the same event
                # on every consecutive video frame.
                if (
                    previous_time is None
                    or now_monotonic - previous_time >= 3.0
                ):

                    self._session_events.append({

                        "timestamp": datetime.now().isoformat(
                            timespec="seconds"
                        ),

                        "elapsed_seconds": round(
                            elapsed, 2
                        ),

                        "event": event_text

                    })

                    self._last_observation_event[
                        event_text
                    ] = now_monotonic

    # ==========================================
    # 6. MAIN VIDEO PROCESSING PIPELINE
    # ==========================================

    def recv(self, frame):

        # Convert incoming webcam frame to OpenCV format.
        image = frame.to_ndarray(format="bgr24")

        # --------------------------------------
        # 1. FACIAL ANALYSIS
        # --------------------------------------

        image, face_detected, face_features = analyze_face(
            image,
            return_features=True
        )

        # --------------------------------------
        # 2. BODY POSTURE ANALYSIS
        # --------------------------------------

        image, pose_detected, pose_data = analyze_pose(
            image
        )

        # --------------------------------------
        # 3. HAND DETECTION
        # --------------------------------------

        image, hands_detected, hand_data = analyze_hands(
            image
        )

        # --------------------------------------
        # 4. EXTRACT BODY FEATURES
        # --------------------------------------

        features = extract_features(
            pose_data,
            hand_data
        )

        # --------------------------------------
        # 5. COMBINE FACIAL AND BODY FEATURES
        # --------------------------------------

        features.update(face_features)

        features["face_detected"] = face_detected

        features["pose_detected"] = pose_detected

        features["hands_detected_status"] = hands_detected

        # --------------------------------------
        # 6. UPDATE OBSERVATION ENGINE
        # --------------------------------------

        observations = self.engine.update(features)

        # --------------------------------------
        # 7. COLLECT LATEST MEASUREMENTS
        # --------------------------------------

        metrics = dict(
            self.engine.latest_metrics
        )

        # --------------------------------------
        # 8. UPDATE LIVE INTERFACE DATA
        # --------------------------------------

        with self.lock:

            self._latest_data = {

                "face_detected": face_detected,

                "pose_detected": pose_detected,

                "hands_detected": hands_detected,

                "observations": list(
                    observations or []
                ),

                "metrics": copy.deepcopy(metrics),

                "timestamp": datetime.now().strftime(
                    "%H:%M:%S"
                )
            }

        # --------------------------------------
        # 9. RECORD SESSION DATA
        # --------------------------------------

        # This stores numerical measurements and events
        # only when a session is active.
        #
        # The original webcam frame is never saved.

        self._record_session_data(
            metrics,
            observations
        )

        # --------------------------------------
        # 10. RETURN ANALYSED CAMERA FRAME
        # --------------------------------------

        return av.VideoFrame.from_ndarray(
            image,
            format="bgr24"
        )
