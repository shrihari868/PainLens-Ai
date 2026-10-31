
import cv2
import mediapipe as mp

from pathlib import Path


# ==========================================
# 1. MODEL CONFIGURATION
# ==========================================

MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "hand_landmarker.task"
)

hand_landmarker = None


# ==========================================
# 2. HAND CONNECTIONS
# ==========================================

HAND_CONNECTIONS = [

    # Thumb
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),

    # Index finger
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),

    # Middle finger
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),

    # Ring finger
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),

    # Little finger
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),

    # Palm
    (0, 17)
]


# ==========================================
# 3. LOAD HAND LANDMARKER
# ==========================================

def get_hand_landmarker():

    global hand_landmarker

    if hand_landmarker is None:

        if not MODEL_PATH.exists():

            raise FileNotFoundError(
                f"Hand model not found: {MODEL_PATH}"
            )

        options = mp.tasks.vision.HandLandmarkerOptions(

            base_options=mp.tasks.BaseOptions(
                model_asset_path=str(MODEL_PATH)
            ),

            running_mode=mp.tasks.vision.RunningMode.IMAGE,

            num_hands=2
        )

        hand_landmarker = (
            mp.tasks.vision.HandLandmarker
            .create_from_options(options)
        )

    return hand_landmarker


# ==========================================
# 4. MAIN HAND ANALYSIS FUNCTION
# ==========================================

def analyze_hands(image):

    # Convert BGR image to RGB
    rgb_image = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2RGB
    )

    # Convert image to MediaPipe format
    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_image
    )

    # Run hand detection
    detector = get_hand_landmarker()

    results = detector.detect(mp_image)

    # Initialise outputs
    hands_detected = 0
    hand_data = []

    height, width, _ = image.shape

    # ======================================
    # 5. PROCESS DETECTED HANDS
    # ======================================

    if results.hand_landmarks:

        hands_detected = len(results.hand_landmarks)

        for hand_index, hand in enumerate(
            results.hand_landmarks
        ):

            # Ensure all 21 landmarks are available
            if len(hand) != 21:
                continue

            # ==================================
            # 6. EXTRACT HAND COORDINATES
            # ==================================

            center_x = sum(
                point.x for point in hand
            ) / 21

            center_y = sum(
                point.y for point in hand
            ) / 21

            # Store hand information
            current_hand = {

                "center_x": float(center_x),

                "center_y": float(center_y),

                "wrist_x": float(hand[0].x),

                "wrist_y": float(hand[0].y),

                "index_tip_x": float(hand[8].x),

                "index_tip_y": float(hand[8].y),

                "landmarks": [
                    {
                        "x": float(point.x),
                        "y": float(point.y),
                        "z": float(point.z)
                    }
                    for point in hand
                ]
            }

            # Store handedness when available
            if (
                results.handedness
                and hand_index < len(results.handedness)
                and results.handedness[hand_index]
            ):

                current_hand["handedness"] = (
                    results.handedness[hand_index][0].category_name
                )

            else:

                current_hand["handedness"] = "Unknown"

            hand_data.append(current_hand)

            # ==================================
            # 7. DRAW FINGER CONNECTIONS
            # ==================================

            for start, end in HAND_CONNECTIONS:

                first = hand[start]

                second = hand[end]

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
                        (255, 0, 255),
                        2
                    )

            # ==================================
            # 8. DRAW 21 HAND LANDMARKS
            # ==================================

            for landmark_index, point in enumerate(hand):

                x = int(point.x * width)

                y = int(point.y * height)

                if (
                    0 <= x < width
                    and 0 <= y < height
                ):

                    # Fingertips are drawn slightly larger
                    radius = (
                        6 if landmark_index in
                        [4, 8, 12, 16, 20]
                        else 3
                    )

                    cv2.circle(
                        image,
                        (x, y),
                        radius,
                        (255, 255, 0),
                        -1
                    )

            # ==================================
            # 9. DISPLAY HAND LABEL
            # ==================================

            wrist_x = int(hand[0].x * width)
            wrist_y = int(hand[0].y * height)

            if (
                0 <= wrist_x < width
                and 0 <= wrist_y < height
            ):

                label = current_hand["handedness"]

                cv2.putText(
                    image,
                    label,
                    (wrist_x, max(20, wrist_y - 15)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 0),
                    2
                )

    # ======================================
    # 10. RETURN RESULTS
    # ======================================

    return image, hands_detected, hand_data
