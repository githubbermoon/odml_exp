from __future__ import annotations

import time
from collections.abc import Iterator

from edgepulse.core.models import PerceptionEvent


class MediaPipePerception:
    """OpenCV + MediaPipe perception loop for macOS webcam demos."""

    def __init__(self, camera_index: int = 0, source: str = "mac-webcam") -> None:
        self.camera_index = camera_index
        self.source = source
        self._last_state = ("none", "unknown", "unknown")
        self._state_started = time.perf_counter()

    def events(self) -> Iterator[tuple[PerceptionEvent, object]]:
        try:
            import cv2
            import mediapipe as mp
        except ImportError as exc:
            raise RuntimeError("Install mediapipe and opencv-python to run perception.") from exc

        hands = mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=0.55, min_tracking_confidence=0.55)
        face_mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open camera index {self.camera_index}")

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    continue
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                hand_result = hands.process(rgb)
                face_result = face_mesh.process(rgb)

                gesture, gesture_conf, hand_payload = classify_hand(hand_result)
                head_pose, attention, face_conf, face_payload = classify_face(face_result)
                duration = self._duration_for(gesture, attention, head_pose)

                yield (
                    PerceptionEvent(
                        source=self.source,
                        gesture=gesture,
                        attention=attention,
                        duration=duration,
                        head_pose=head_pose,
                        confidence=max(gesture_conf, face_conf),
                        landmarks={"hand": hand_payload, "face": face_payload},
                    ),
                    frame,
                )
        finally:
            cap.release()
            hands.close()
            face_mesh.close()

    def _duration_for(self, gesture: str, attention: str, head_pose: str) -> float:
        state = (gesture, attention, head_pose)
        now = time.perf_counter()
        if state != self._last_state:
            self._last_state = state
            self._state_started = now
        return now - self._state_started


def classify_hand(result: object) -> tuple[str, float, dict[str, object]]:
    if not getattr(result, "multi_hand_landmarks", None):
        return "none", 0.0, {}

    points = result.multi_hand_landmarks[0].landmark
    tips = [4, 8, 12, 16, 20]
    pip = [3, 6, 10, 14, 18]
    extended = [points[t].y < points[p].y for t, p in zip(tips, pip, strict=True)]
    index_up, middle_up, ring_up, pinky_up = extended[1], extended[2], extended[3], extended[4]
    thumb_right = points[4].x > points[3].x

    wrist_y = points[0].y
    avg_tip_y = sum(points[t].y for t in tips) / len(tips)

    if all(extended[1:]) and avg_tip_y < wrist_y - 0.18:
        gesture = "raised_hand"
    elif index_up and not any([middle_up, ring_up, pinky_up]):
        gesture = "pointing"
    elif extended[0] and not any(extended[1:]) and points[4].y < points[3].y:
        gesture = "thumbs_up"
    elif extended[0] and not any(extended[1:]) and points[4].y > points[3].y:
        gesture = "thumbs_down"
    elif all(extended[1:]) and thumb_right:
        gesture = "open_palm"
    else:
        gesture = "none"

    payload = {
        "extended": extended,
        "wrist": {"x": points[0].x, "y": points[0].y},
        "index_tip": {"x": points[8].x, "y": points[8].y},
    }
    return gesture, 0.78 if gesture != "none" else 0.35, payload


def classify_face(result: object) -> tuple[str, str, float, dict[str, object]]:
    if not getattr(result, "multi_face_landmarks", None):
        return "unknown", "unknown", 0.0, {}

    points = result.multi_face_landmarks[0].landmark
    left_eye = points[33]
    right_eye = points[263]
    nose = points[1]
    chin = points[152]
    eye_slope = left_eye.y - right_eye.y
    vertical = chin.y - nose.y

    if eye_slope > 0.035:
        head_pose = "tilted_left"
    elif eye_slope < -0.035:
        head_pose = "tilted_right"
    elif vertical < 0.16:
        head_pose = "looking_down"
    elif nose.x < 0.40 or nose.x > 0.60:
        head_pose = "looking_away"
    else:
        head_pose = "center"

    if head_pose == "center":
        attention = "focused"
    elif head_pose in {"tilted_left", "tilted_right"}:
        attention = "confused"
    elif head_pose == "looking_away":
        attention = "away"
    else:
        attention = "focused"

    payload = {
        "nose": {"x": nose.x, "y": nose.y},
        "eye_slope": eye_slope,
        "vertical": vertical,
    }
    return head_pose, attention, 0.7, payload
