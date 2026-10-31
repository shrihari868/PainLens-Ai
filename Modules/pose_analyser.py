
import cv2
import mediapipe as mp
from pathlib import Path


# ==========================================
# 1. MODEL CONFIGURATION
# ==========================================

MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "pose_landmarker_lite.task"
)

pose_landmarker = None


# ==========================================
# 2. BODY CONNECTIONS
# ==========================================

POSE_CONNECTIONS = [
    (11, 12),  # Shoulders

    (11, 13),  # Left upper arm
    (13, 15),  # Left forearm

    (12, 14),  # Right upper arm
    (14, 16),  # Right forearm

    (11, 23),  # Left torso
    (12, 24),  # Right torso

    (23, 24),  # Hips

    (23, 25),  # Left thigh
    (25, 27),  # Left lower leg

    (24, 26),  # Right thigh
    (26, 28),  # Right lower leg

    (27, 29),  # Left ankle to heel
    (28, 30),  # Right ankle to heel

    (29, 31),  # Left foot
    (30, 32)   # Right foot
]


# ==========================================
# 3. LOAD POSE LANDMARKER
# ==========================================

def get_pose_landmarker():

    global pose_landmarker

    if pose_landmarker is None:

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Pose model not found: {MODEL_PATH}"
            )

        options = mp.tasks.vision.PoseLandmarkerOptions(

            base_options=mp.tasks.BaseOptions(
                model_asset_path=str(MODEL_PATH)
            ),

            running_mode=mp.tasks.vision.RunningMode.IMAGE,

            num_poses=1
        )

        pose_landmarker = (
            mp.tasks.vision.PoseLandmarker
            .create_from_options(options)
        )

    return pose_landmarker


# ==========================================
# 4. MAIN POSE ANALYSIS FUNCTION
# ==========================================

def analyze_pose(image):

    # Convert BGR to RGB
    rgb_image = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2RGB
    )

    # Convert to MediaPipe image
    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_image
    )

    # Run pose detection
    detector = get_pose_landmarker()

    results = detector.detect(mp_image)

    pose_detected = False
    pose_data = None

    # ======================================
    # 5. PROCESS DETECTED BODY
    # ======================================

    if results.pose_landmarks:

        pose_detected = True

        height, width, _ = image.shape

        landmarks = results.pose_landmarks[0]

        # ==================================
        # 6. EXTRACT BODY LANDMARK DATA
        # ==================================

        landmark_indices = {

            "left_shoulder": 11,
            "right_shoulder": 12,

            "left_elbow": 13,
            "right_elbow": 14,

            "left_wrist": 15,
            "right_wrist": 16,

            "left_hip": 23,
            "right_hip": 24,

            "left_knee": 25,
            "right_knee": 26,

            "left_ankle": 27,
            "right_ankle": 28
        }

        pose_data = {}

        for name, index in landmark_indices.items():

            point = landmarks[index]

            visibility = getattr(
                point,
                "visibility",
                0.0
            )

            pose_data[name] = {

                "x": float(point.x),

                "y": float(point.y),

                "visibility": float(visibility)
            }

        # ==================================
        # 7. DRAW BODY CONNECTIONS
        # ==================================

        for start, end in POSE_CONNECTIONS:

            first = landmarks[start]

            second = landmarks[end]

            visibility_first = getattr(
                first,
                "visibility",
                0.0
            )

            visibility_second = getattr(
                second,
                "visibility",
                0.0
            )

            if (
                visibility_first > 0.5
                and visibility_second > 0.5
            ):

                x1 = int(first.x * width)
                y1 = int(first.y * height)

                x2 = int(second.x * width)
                y2 = int(second.y * height)

                if (
                    0 <= x1 < width
                    and 0 <= y1 < height
                    and 0 <= x2 < width
                    and 0 <= y2 < height
                ):

                    cv2.line(
                        image,
                        (x1, y1),
                        (x2, y2),
                        (255, 180, 0),
                        2
                    )

        # ==================================
        # 8. DRAW BODY JOINTS
        # ==================================

        # Landmarks 0-10 represent the face.
        # We deliberately skip them.

        for index, landmark in enumerate(landmarks):

            if index <= 10:
                continue

            visibility = getattr(
                landmark,
                "visibility",
                0.0
            )

            if visibility > 0.5:

                x = int(landmark.x * width)

                y = int(landmark.y * height)

                if (
                    0 <= x < width
                    and 0 <= y < height
                ):

                    cv2.circle(
                        image,
                        (x, y),
                        4,
                        (0, 255, 255),
                        -1
                    )

    # ======================================
    # 9. RETURN RESULTS
    # ======================================

    return image, pose_detected, pose_data
