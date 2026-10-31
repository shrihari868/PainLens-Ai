
import cv2
import mediapipe as mp
from pathlib import Path

# Locate the downloaded AI model
MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "face_landmarker.task"
)

# Store the detector so it is not recreated for every frame
face_landmarker = None


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


def analyze_face(image):

    # Convert OpenCV BGR image to RGB
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

        height, width, _ = image.shape

        for face in results.face_landmarks:

            for landmark in face:

                x = int(landmark.x * width)
                y = int(landmark.y * height)

                # Draw each detected facial landmark
                if 0 <= x < width and 0 <= y < height:

                    cv2.circle(
                        image,
                        (x, y),
                        1,
                        (0, 255, 0),
                        -1
                    )

    return image, face_detected
