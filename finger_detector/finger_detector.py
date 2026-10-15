"""Hand detection with MediaPipe: turns a camera frame into 5 finger states.

Output order is always (thumb, index, middle, ring, pinky), 1 = raised, 0 = down.
"""

import time
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarksConnections, drawing_utils

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
)

FINGER_NAMES = ("thumb", "index", "middle", "ring", "pinky")
NO_HAND = (0, 0, 0, 0, 0)

# MediaPipe landmark indices (see the report for the full 21-point map).
THUMB_IP, THUMB_TIP = 3, 4
INDEX_MCP, PINKY_MCP = 5, 17
FINGER_TIPS = (8, 12, 16, 20)  # index, middle, ring, pinky
FINGER_PIPS = (6, 10, 14, 18)  # the middle joint of each of those fingers


def ensure_model(path: Path) -> None:
    """Download the hand model (~8 MB) the first time the program runs."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[Detector] Downloading hand model to {path} ...")
    urllib.request.urlretrieve(MODEL_URL, path)
    print("[Detector] Model downloaded.")


def finger_states(landmarks) -> tuple[int, int, int, int, int]:
    """Decide which fingers are raised from the 21 hand landmarks.

    Image coordinates: x grows to the right, y grows DOWNWARDS, so a raised
    finger has its tip *above* (smaller y than) its middle joint.
    """
    # Thumb: it moves sideways, not up. Compare the thumb's sideways movement
    # with the direction "pinky -> index" across the palm. If the tip is further
    # out on the index side than the joint below it, the thumb is open.
    # This works for left and right hands, palm or back facing the camera.
    palm_direction = landmarks[INDEX_MCP].x - landmarks[PINKY_MCP].x
    thumb_direction = landmarks[THUMB_TIP].x - landmarks[THUMB_IP].x
    thumb = int(palm_direction * thumb_direction > 0)

    others = [
        int(landmarks[tip].y < landmarks[pip].y)
        for tip, pip in zip(FINGER_TIPS, FINGER_PIPS)
    ]
    return (thumb, *others)


class FingerDetector:
    def __init__(self, model_path: Path, detection_confidence: float, tracking_confidence: float):
        ensure_model(model_path)
        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=detection_confidence,
            min_hand_presence_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._start = time.monotonic()
        self._last_timestamp_ms = -1

    def detect(self, frame_bgr):
        """Return (finger_states, landmarks). landmarks is None when no hand is seen."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)  # OpenCV is BGR, MediaPipe wants RGB
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # VIDEO mode needs a strictly increasing timestamp for each frame.
        timestamp_ms = int((time.monotonic() - self._start) * 1000)
        timestamp_ms = max(timestamp_ms, self._last_timestamp_ms + 1)
        self._last_timestamp_ms = timestamp_ms

        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.hand_landmarks:
            return NO_HAND, None

        landmarks = result.hand_landmarks[0]
        return finger_states(landmarks), landmarks

    @staticmethod
    def draw(frame_bgr, landmarks) -> None:
        drawing_utils.draw_landmarks(frame_bgr, landmarks, HandLandmarksConnections.HAND_CONNECTIONS)

    def close(self) -> None:
        self._landmarker.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class StateStabilizer:
    """Ignores one-frame flickers: a new state is only accepted after it has
    been seen `required_frames` frames in a row."""

    def __init__(self, required_frames: int):
        self.required_frames = required_frames
        self.current = NO_HAND
        self._candidate = NO_HAND
        self._count = 0

    def update(self, states: tuple[int, ...]) -> tuple[int, ...]:
        if states != self._candidate:
            self._candidate = states
            self._count = 0
        self._count += 1
        if self._count >= self.required_frames:
            self.current = self._candidate
        return self.current
