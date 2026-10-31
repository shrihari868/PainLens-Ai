
from collections import deque
import time


class ObservationEngine:

    def __init__(self):

        # Keep the latest 5 seconds of measurements
        self.window_seconds = 5.0
        self.samples = deque()

        # Minimum change required for a posture event
        self.angle_threshold = 12.0

        # Approximate image-distance threshold
        self.hand_near_threshold = 0.16

        # Avoid repeatedly reporting the same event
        self.cooldown_seconds = 3.0
        self.last_event_time = {}

        self.previous_hand_near = None

    def can_report(self, event_name, current_time):

        previous_time = self.last_event_time.get(
            event_name, 0
        )

        if current_time - previous_time >= self.cooldown_seconds:

            self.last_event_time[event_name] = current_time
            return True

        return False

    def update(self, features):

        current_time = time.monotonic()
        observations = []

        angle = features.get("torso_inclination")
        hand_distance = features.get(
            "hand_to_torso_distance"
        )
        quality = features.get("tracking_quality")

        # Remove old samples
        while self.samples and (
            current_time - self.samples[0]["time"]
            > self.window_seconds
        ):
            self.samples.popleft()

        # Check tracking quality before analysing posture
        if quality is not None and quality >= 0.45:

            if angle is not None:

                # Compare current angle with recent observations
                previous_angles = [
                    sample["angle"]
                    for sample in self.samples
                    if sample["angle"] is not None
                ]

                if len(previous_angles) >= 5:

                    recent_angles = previous_angles[-10:]

                    average_angle = (
                        sum(recent_angles)
                        / len(recent_angles)
                    )

                    angle_change = abs(
                        float(angle) - average_angle
                    )

                    if (
                        angle_change >= self.angle_threshold
                        and self.can_report(
                            "posture_change",
                            current_time
                        )
                    ):

                        observations.append(
                            "Noticeable torso angle change observed"
                        )

                self.samples.append({
                    "time": current_time,
                    "angle": float(angle)
                })

        # Observe hand proximity
        if hand_distance is not None:

            hand_near = (
                float(hand_distance)
                < self.hand_near_threshold
            )

            if (
                hand_near
                and self.previous_hand_near is False
                and self.can_report(
                    "hand_proximity",
                    current_time
                )
            ):

                observations.append(
                    "Hand entered the torso-proximity zone"
                )

            self.previous_hand_near = hand_near

        return observations
