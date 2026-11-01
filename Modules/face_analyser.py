
import cv2
import mediapipe as mp
import math
from pathlib import Path


# ==================================================
# 1. FACE MODEL LOCATION
# ==================================================

MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "face_landmarker.task"
)

# Reuse the detector instead of recreating it per frame
face_landmarker = None


# ==================================================
# 2. INITIALIZE FACE DETECTOR
# ==================================================

def get_face_landmarker():

    global face_landmarker

    if face_landmarker is None:

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Face model not found: {MODEL_PATH}"
            )

        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=str(MODEL_PATH)
            ),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_faces=1
        )

        face_landmarker = (
            mp.tasks.vision.FaceLandmarker
            .create_from_options(options)
        )

    return face_landmarker


# ==================================================
# 3. LANDMARK DISTANCE CALCULATION
# ==================================================

def calculate_distance(point1, point2):

    return math.hypot(
        point1[0] - point2[0],
        point1[1] - point2[1]
    )


# ==================================================
# 4. EYE ASPECT RATIO (EAR)
# ==================================================

def calculate_ear(landmarks, eye_indices, width, height):

    points = []

    for index in eye_indices:

        landmark = landmarks[index]

        points.append((
            landmark.x * width,
            landmark.y * height
        ))

    horizontal_distance = calculate_distance(
        points[0],
        points[3]
    )

    if horizontal_distance == 0:
        return None

    vertical_distance_1 = calculate_distance(
        points[1],
        points[5]
    )

    vertical_distance_2 = calculate_distance(
        points[2],
        points[4]
    )

    ear = (
        vertical_distance_1 + vertical_distance_2
    ) / (2.0 * horizontal_distance)

    return round(ear, 4)


# ==================================================
# 5. MOUTH ASPECT RATIO (MAR)
# ==================================================

def calculate_mar(landmarks, width, height):

    upper_lip = landmarks[13]
    lower_lip = landmarks[14]

    left_corner = landmarks[61]
    right_corner = landmarks[291]

    upper_point = (
        upper_lip.x * width,
        upper_lip.y * height
    )

    lower_point = (
        lower_lip.x * width,
        lower_lip.y * height
    )

    left_point = (
        left_corner.x * width,
        left_corner.y * height
    )

    right_point = (
        right_corner.x * width,
        right_corner.y * height
    )

    mouth_height = calculate_distance(
        upper_point,
        lower_point
    )

    mouth_width = calculate_distance(
        left_point,
        right_point
    )

    if mouth_width == 0:
        return None

    mar = mouth_height / mouth_width

    return round(mar, 4)


# ==================================================
# 6. FACIAL GEOMETRY
# ==================================================

def calculate_facial_geometry(
    landmarks,
    width,
    height
):

    # Outer eye corners
    left_eye = (
        landmarks[33].x * width,
        landmarks[33].y * height
    )

    right_eye = (
        landmarks[263].x * width,
        landmarks[263].y * height
    )

    # Nose reference point
    nose = (
        landmarks[1].x * width,
        landmarks[1].y * height
    )

    # Mouth corners
    left_mouth = (
        landmarks[61].x * width,
        landmarks[61].y * height
    )

    right_mouth = (
        landmarks[291].x * width,
        landmarks[291].y * height
    )

    eye_midpoint = (
        (left_eye[0] + right_eye[0]) / 2,
        (left_eye[1] + right_eye[1]) / 2
    )

    mouth_midpoint = (
        (left_mouth[0] + right_mouth[0]) / 2,
        (left_mouth[1] + right_mouth[1]) / 2
    )

    interocular_distance = calculate_distance(
        left_eye,
        right_eye
    )

    if interocular_distance == 0:
        return {}

    nose_to_eye_ratio = (
        calculate_distance(
            nose,
            eye_midpoint
        ) / interocular_distance
    )

    nose_to_mouth_ratio = (
        calculate_distance(
            nose,
            mouth_midpoint
        ) / interocular_distance
    )

    # Estimate 2D head roll from the eye line
    head_roll = math.degrees(
        math.atan2(
            right_eye[1] - left_eye[1],
            right_eye[0] - left_eye[0]
        )
    )

    return {
        "interocular_distance": round(
            interocular_distance, 2
        ),

        "nose_to_eye_ratio": round(
            nose_to_eye_ratio, 4
        ),

        "nose_to_mouth_ratio": round(
            nose_to_mouth_ratio, 4
        ),

        "head_roll_degrees": round(
            head_roll, 2
        )
    }


# ==================================================
# 7. MAIN FACIAL ANALYSIS
# ==================================================

def analyze_face(image, return_features=False):

    height, width, _ = image.shape

    # Default measurements when no face is detected
    face_features = {
        "left_ear": None,
        "right_ear": None,
        "eye_aspect_ratio": None,
        "mouth_aspect_ratio": None,
        "interocular_distance": None,
        "nose_to_eye_ratio": None,
        "nose_to_mouth_ratio": None,
        "head_roll_degrees": None,
        "landmark_count": 0
    }

    # Convert OpenCV BGR image into RGB
    rgb_image = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2RGB
    )

    # Convert image into MediaPipe format
    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_image
    )

    # Detect facial landmarks
    detector = get_face_landmarker()
    results = detector.detect(mp_image)

    face_detected = False

    if results.face_landmarks:

        face_detected = True

        for face in results.face_landmarks:

            face_features["landmark_count"] = len(face)

            # Ensure required landmarks exist
            if len(face) >= 468:

                # ----------------------------------
                # LEFT AND RIGHT EYE MEASUREMENTS
                # ----------------------------------

                left_eye_indices = [
                    362, 385, 387,
                    263, 373, 380
                ]

                right_eye_indices = [
                    33, 160, 158,
                    133, 153, 144
                ]

                left_ear = calculate_ear(
                    face,
                    left_eye_indices,
                    width,
                    height
                )

                right_ear = calculate_ear(
                    face,
                    right_eye_indices,
                    width,
                    height
                )

                face_features["left_ear"] = left_ear
                face_features["right_ear"] = right_ear

                valid_ears = [
                    value
                    for value in [left_ear, right_ear]
                    if value is not None
                ]

                if valid_ears:

                    face_features["eye_aspect_ratio"] = round(
                        sum(valid_ears) / len(valid_ears),
                        4
                    )

                # ----------------------------------
                # MOUTH OPENING MEASUREMENT
                # ----------------------------------

                face_features["mouth_aspect_ratio"] = (
                    calculate_mar(
                        face,
                        width,
                        height
                    )
                )

                # ----------------------------------
                # EYE-NOSE-MOUTH GEOMETRY
                # ----------------------------------

                geometry = calculate_facial_geometry(
                    face,
                    width,
                    height
                )

                face_features.update(geometry)

            # --------------------------------------
            # DRAW FACIAL LANDMARKS
            # --------------------------------------

            for landmark in face:

                x = int(landmark.x * width)
                y = int(landmark.y * height)

                if 0 <= x < width and 0 <= y < height:

                    cv2.circle(
                        image,
                        (x, y),
                        1,
                        (0, 255, 0),
                        -1
                    )

    # ----------------------------------------------
    # BACKWARD-COMPATIBLE RETURN
    # ----------------------------------------------

    # Existing video_processor.py expects two values.
    # Keep that behaviour until we update its caller.

    if return_features:

        return image, face_detected, face_features

    return image, face_detected
