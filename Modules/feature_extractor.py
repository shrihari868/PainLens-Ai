
import math


def calculate_distance(point1, point2):

    dx = point1["x"] - point2["x"]
    dy = point1["y"] - point2["y"]

    return math.sqrt(dx**2 + dy**2)


def extract_features(pose_data, hand_data):

    features = {
        "torso_inclination": None,
        "hand_to_torso_distance": None,
        "hands_detected": len(hand_data),
        "tracking_quality": None
    }

    if not pose_data:
        return features

    required = [
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip"
    ]

    # Ensure important landmarks are available
    if not all(name in pose_data for name in required):
        return features

    # Calculate average landmark visibility
    visibility_values = [
        pose_data[name]["visibility"]
        for name in pose_data
    ]

    if visibility_values:

        features["tracking_quality"] = round(
            sum(visibility_values) / len(visibility_values),
            3
        )

    # Calculate shoulder midpoint
    shoulder_mid = {
        "x": (
            pose_data["left_shoulder"]["x"]
            + pose_data["right_shoulder"]["x"]
        ) / 2,

        "y": (
            pose_data["left_shoulder"]["y"]
            + pose_data["right_shoulder"]["y"]
        ) / 2
    }

    # Calculate hip midpoint
    hip_mid = {
        "x": (
            pose_data["left_hip"]["x"]
            + pose_data["right_hip"]["x"]
        ) / 2,

        "y": (
            pose_data["left_hip"]["y"]
            + pose_data["right_hip"]["y"]
        ) / 2
    }

    # Calculate torso inclination
    dx = shoulder_mid["x"] - hip_mid["x"]
    dy = hip_mid["y"] - shoulder_mid["y"]

    angle = math.degrees(math.atan2(dx, dy))

    features["torso_inclination"] = round(
        angle, 2
    )

    # Calculate distance from hands to torso
    if hand_data:

        distances = []

        for hand in hand_data:

            hand_center = {
                "x": hand["center_x"],
                "y": hand["center_y"]
            }

            shoulder_distance = calculate_distance(
                hand_center,
                shoulder_mid
            )

            hip_distance = calculate_distance(
                hand_center,
                hip_mid
            )

            distances.append(
                min(
                    shoulder_distance,
                    hip_distance
                )
            )

        features["hand_to_torso_distance"] = round(
            min(distances), 4
        )

    return features
