"""Application settings, loaded from the .env file.

Every value that can change between machines (broker IP, camera index, ...)
lives in .env, so the code never needs to be edited to run somewhere else.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


def _get_str(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _get_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _get_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    # MQTT
    mqtt_host: str
    mqtt_port: int
    mqtt_topic: str
    mqtt_client_id: str
    mqtt_username: str | None
    mqtt_password: str | None

    # Camera / display
    camera_index: int
    show_preview: bool

    # Hand detection
    model_path: Path
    detection_confidence: float
    tracking_confidence: float
    stable_frames: int


def load_settings() -> Settings:
    model_path = Path(_get_str("MODEL_PATH", "models/hand_landmarker.task"))
    if not model_path.is_absolute():
        model_path = BASE_DIR / model_path

    return Settings(
        mqtt_host=_get_str("MQTT_HOST", "localhost"),
        mqtt_port=_get_int("MQTT_PORT", 1883),
        mqtt_topic=_get_str("MQTT_TOPIC", "hand/gesture"),
        mqtt_client_id=_get_str("MQTT_CLIENT_ID", "finger-detector-pc"),
        mqtt_username=_get_str("MQTT_USERNAME", "") or None,
        mqtt_password=_get_str("MQTT_PASSWORD", "") or None,
        camera_index=_get_int("CAMERA_INDEX", 0),
        show_preview=_get_bool("SHOW_PREVIEW", True),
        model_path=model_path,
        detection_confidence=_get_float("DETECTION_CONFIDENCE", 0.7),
        tracking_confidence=_get_float("TRACKING_CONFIDENCE", 0.7),
        stable_frames=max(1, _get_int("STABLE_FRAMES", 2)),
    )
