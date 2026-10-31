
import cv2
import av

from datetime import datetime
from streamlit_webrtc import VideoProcessorBase

from Modules.face_analyser import analyze_face
from Modules.pose_analyser import analyze_pose
from Modules.hand_analyser import analyze_hands
from Modules.feature_extractor import extract_features
from Modules.observation_engine import ObservationEngine


class VideoProcessor(VideoProcessorBase):

    def __init__(self):
        # Initialise the temporal observation engine
        self.observation_engine = ObservationEngine()

    def recv(self, frame):

        # ------------------------------------------------
        # 1. CONVERT INCOMING VIDEO FRAME
        # ------------------------------------------------

        image = frame.to_ndarray(format="bgr24")

        # ------------------------------------------------
        # 2. FACE DETECTION
        # ------------------------------------------------

        image, face_detected = analyze_face(image)

        # ------------------------------------------------
        # 3. BODY POSE DETECTION
        # ------------------------------------------------

        image, pose_detected, pose_data = analyze_pose(image)

        # ------------------------------------------------
        # 4. HAND DETECTION
        # ------------------------------------------------

        image, hands_detected, hand_data = analyze_hands(image)

        # ------------------------------------------------
        # 5. FEATURE EXTRACTION
        # ------------------------------------------------

        features = extract_features(
            pose_data,
            hand_data
        )

        # ------------------------------------------------
        # 6. TEMPORAL BEHAVIOURAL ANALYSIS
        # ------------------------------------------------

        observations = self.observation_engine.update(
            features
        )

        # ------------------------------------------------
        # 7. APPLICATION HEADING
        # ------------------------------------------------

        cv2.putText(
            image,
            "PAINSENSE AI - LIVE ANALYSIS",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        # ------------------------------------------------
        # 8. FACE DETECTION STATUS
        # ------------------------------------------------

        face_status = (
            "FACE: DETECTED"
            if face_detected
            else "FACE: NOT DETECTED"
        )

        cv2.putText(
            image,
            face_status,
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0) if face_detected else (0, 0, 255),
            2
        )

        # ------------------------------------------------
        # 9. BODY DETECTION STATUS
        # ------------------------------------------------

        pose_status = (
            "BODY: DETECTED"
            if pose_detected
            else "BODY: NOT DETECTED"
        )

        cv2.putText(
            image,
            pose_status,
            (20, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255) if pose_detected else (0, 0, 255),
            2
        )

        # ------------------------------------------------
        # 10. HAND DETECTION STATUS
        # ------------------------------------------------

        cv2.putText(
            image,
            f"HANDS DETECTED: {hands_detected}",
            (20, 145),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 0, 255),
            2
        )

        # ------------------------------------------------
        # 11. TORSO INCLINATION
        # ------------------------------------------------

        torso_angle = features.get(
            "torso_inclination"
        )

        if torso_angle is not None:
            torso_text = f"Torso angle: {torso_angle} deg"
        else:
            torso_text = "Torso angle: Unavailable"

        cv2.putText(
            image,
            torso_text,
            (20, 190),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )

        # ------------------------------------------------
        # 12. HAND-TO-TORSO DISTANCE
        # ------------------------------------------------

        hand_distance = features.get(
            "hand_to_torso_distance"
        )

        if hand_distance is not None:
            distance_text = (
                f"Hand distance: {hand_distance}"
            )
        else:
            distance_text = "Hand distance: Unavailable"

        cv2.putText(
            image,
            distance_text,
            (20, 220),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )

        # ------------------------------------------------
        # 13. TRACKING QUALITY
        # ------------------------------------------------

        tracking_quality = features.get(
            "tracking_quality"
        )

        if tracking_quality is not None:

            quality_percentage = tracking_quality * 100

            quality_text = (
                f"Body tracking: {quality_percentage:.1f}%"
            )

        else:
            quality_text = "Body tracking: Unavailable"

        cv2.putText(
            image,
            quality_text,
            (20, 250),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )

        # ------------------------------------------------
        # 14. BEHAVIOURAL OBSERVATIONS
        # ------------------------------------------------

        if observations:

            observation_text = observations[-1]

            observation_color = (0, 255, 255)

        else:

            observation_text = "Monitoring movements..."

            observation_color = (255, 255, 255)

        cv2.putText(
            image,
            observation_text[:55],
            (20, 315),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            observation_color,
            1
        )

        # ------------------------------------------------
        # 15. CURRENT TIME
        # ------------------------------------------------

        current_time = datetime.now().strftime(
            "%H:%M:%S"
        )

        cv2.putText(
            image,
            current_time,
            (20, 280),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )

        # ------------------------------------------------
        # 16. RETURN PROCESSED VIDEO
        # ------------------------------------------------

        return av.VideoFrame.from_ndarray(
            image,
            format="bgr24"
        )
