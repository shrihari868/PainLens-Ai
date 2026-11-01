import time
from collections import deque


class ObservationEngine:
    def __init__(
        self,
        window_seconds=60,
        angle_threshold=12,
        hand_near_threshold=0.16,
        cooldown=3
    ):
        self.window_seconds = window_seconds
        self.angle_threshold = angle_threshold
        self.hand_near_threshold = hand_near_threshold
        self.cooldown = cooldown

        self.monitoring_start_time = time.monotonic()

        # Facial observation state
        self.eye_closed = False
        self.eye_closed_start = None
        self.blink_events = deque()
        self.blink_count = 0

        self.eye_close_threshold = 0.20
        self.eye_open_threshold = 0.23
        self.minimum_blink_duration = 0.08
        self.maximum_blink_duration = 0.80

        self.mouth_open = False
        self.mouth_open_start = None
        self.mouth_open_events = deque()
        self.mouth_open_threshold = 0.25
        self.sustained_mouth_threshold = 3.0

        # Facial geometry tracking
        self.previous_geometry = None

        # Body observation tracking
        self.samples = deque()
        self.last_torso_angle = None

        # Prevent repeated alerts
        self.last_reported = {}

        # Latest measurements for the Streamlit interface
        self.latest_metrics = {}

    def can_report(self, event_name, current_time):
        last_time = self.last_reported.get(event_name)

        if last_time is None or current_time - last_time >= self.cooldown:
            self.last_reported[event_name] = current_time
            return True

        return False

    def clean_events(self, event_queue, current_time):
        while event_queue and current_time - event_queue[0] > self.window_seconds:
            event_queue.popleft()

    def reset_face_tracking(self):
        """
        Reset temporary facial states when a face is not detected.
        Do not count an incomplete eye closure as a blink.
        """
        self.eye_closed = False
        self.eye_closed_start = None

        self.mouth_open = False
        self.mouth_open_start = None

        self.previous_geometry = None

    def analyze_eyes(self, features, current_time):
        ear = features.get("eye_aspect_ratio")

        result = {
            "eye_aspect_ratio": ear,
            "left_ear": features.get("left_ear"),
            "right_ear": features.get("right_ear"),
            "eye_status": "Unavailable",
            "eye_closure_duration": 0.0,
            "blink_count": self.blink_count,
            "blink_rate": None
        }

        if ear is None:
            return result

        # Hysteresis prevents rapid switching around one threshold.
        if not self.eye_closed and ear < self.eye_close_threshold:
            self.eye_closed = True
            self.eye_closed_start = current_time

        elif self.eye_closed and ear > self.eye_open_threshold:
            if self.eye_closed_start is not None:
                duration = current_time - self.eye_closed_start

                # Count only closures within the configured blink range.
                if (
                    self.minimum_blink_duration
                    <= duration
                    <= self.maximum_blink_duration
                ):
                    self.blink_count += 1
                    self.blink_events.append(current_time)

            self.eye_closed = False
            self.eye_closed_start = None

        if self.eye_closed:
            result["eye_status"] = "Eyes closed"
            if self.eye_closed_start is not None:
                result["eye_closure_duration"] = round(
                    current_time - self.eye_closed_start, 2
                )
        else:
            result["eye_status"] = "Eyes open"

        self.clean_events(self.blink_events, current_time)

        # Show a rolling 60-second rate only after a full 60-second baseline.
        elapsed = current_time - self.monitoring_start_time

        if elapsed >= self.window_seconds:
            result["blink_rate"] = len(self.blink_events)

        result["blink_count"] = self.blink_count

        return result

    def analyze_mouth(self, features, current_time):
        mar = features.get("mouth_aspect_ratio")

        result = {
            "mouth_aspect_ratio": mar,
            "mouth_status": "Unavailable",
            "mouth_open_duration": 0.0,
            "mouth_open_frequency": 0,
            "possible_sustained_mouth_opening": False
        }

        if mar is None:
            return result

        if not self.mouth_open and mar > self.mouth_open_threshold:
            self.mouth_open = True
            self.mouth_open_start = current_time
            self.mouth_open_events.append(current_time)

        elif self.mouth_open and mar <= self.mouth_open_threshold:
            self.mouth_open = False
            self.mouth_open_start = None

        self.clean_events(self.mouth_open_events, current_time)

        result["mouth_open_frequency"] = len(self.mouth_open_events)

        if self.mouth_open:
            result["mouth_status"] = "Mouth open"

            if self.mouth_open_start is not None:
                duration = current_time - self.mouth_open_start
                result["mouth_open_duration"] = round(duration, 2)

                result["possible_sustained_mouth_opening"] = (
                    duration >= self.sustained_mouth_threshold
                )
        else:
            result["mouth_status"] = "Mouth closed"

        return result

    def analyze_geometry(self, features):
        geometry = {
            "nose_to_eye_ratio": features.get("nose_to_eye_ratio"),
            "nose_to_mouth_ratio": features.get("nose_to_mouth_ratio"),
            "head_roll_degrees": features.get("head_roll_degrees")
        }

        change = None

        current_values = [
            geometry["nose_to_eye_ratio"],
            geometry["nose_to_mouth_ratio"]
        ]

        if all(value is not None for value in current_values):
            if self.previous_geometry is not None:
                previous_values = self.previous_geometry

                change = round(
                    abs(current_values[0] - previous_values[0])
                    + abs(current_values[1] - previous_values[1]),
                    4
                )

            self.previous_geometry = current_values

        geometry["facial_geometry_change"] = change

        return geometry

    def update(self, features):
        current_time = time.monotonic()
        observations = []

        face_detected = features.get("face_detected", False)

        # -------------------------------------------------
        # FACIAL OBSERVATIONS
        # -------------------------------------------------
        if face_detected:
            eye_metrics = self.analyze_eyes(features, current_time)
            mouth_metrics = self.analyze_mouth(features, current_time)
            geometry_metrics = self.analyze_geometry(features)
        else:
            self.reset_face_tracking()

            eye_metrics = {
                "eye_aspect_ratio": None,
                "left_ear": None,
                "right_ear": None,
                "eye_status": "Face not detected",
                "eye_closure_duration": 0.0,
                "blink_count": self.blink_count,
                "blink_rate": None
            }

            mouth_metrics = {
                "mouth_aspect_ratio": None,
                "mouth_status": "Face not detected",
                "mouth_open_duration": 0.0,
                "mouth_open_frequency": len(self.mouth_open_events),
                "possible_sustained_mouth_opening": False
            }

            geometry_metrics = {
                "nose_to_eye_ratio": None,
                "nose_to_mouth_ratio": None,
                "head_roll_degrees": None,
                "facial_geometry_change": None
            }

        # -------------------------------------------------
        # BODY OBSERVATIONS
        # -------------------------------------------------
        torso_angle = features.get("torso_inclination")
        hand_distance = features.get("hand_to_torso_distance")

        if torso_angle is not None:
            if self.last_torso_angle is not None:
                angle_change = abs(torso_angle - self.last_torso_angle)

                if (
                    angle_change >= self.angle_threshold
                    and self.can_report("posture_change", current_time)
                ):
                    observations.append(
                        "Noticeable change in torso inclination"
                    )

            self.last_torso_angle = torso_angle

        if (
            hand_distance is not None
            and hand_distance <= self.hand_near_threshold
            and self.can_report("hand_near_torso", current_time)
        ):
            observations.append(
                "Hand detected near the torso"
            )

        body_metrics = {
            "torso_inclination": torso_angle,
            "hand_to_torso_distance": hand_distance,
            "hands_detected": features.get("hands_detected", 0),
            "tracking_quality": features.get("tracking_quality")
        }

        # -------------------------------------------------
        # COMBINE LATEST METRICS FOR THE DASHBOARD
        # -------------------------------------------------
        self.latest_metrics = {
            **eye_metrics,
            **mouth_metrics,
            **geometry_metrics,
            **body_metrics,
            "face_detected": face_detected,
            "pose_detected": features.get("pose_detected", False),
            "hands_detected_status": features.get(
                "hands_detected_status", False
            )
        }

        return observations