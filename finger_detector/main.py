"""Entry point: camera -> finger detection -> MQTT -> ESP32 LEDs.

Run:  python main.py      (press Esc or Q in the video window to quit)
"""

import time

import cv2

from config import load_settings
from finger_detector import FINGER_NAMES, FingerDetector, StateStabilizer
from mqtt_client import MqttPublisher, encode_states

ESC_KEY = 27
GREEN = (0, 200, 0)
RED = (0, 0, 255)
GRAY = (160, 160, 160)


def draw_overlay(frame, states, fps: float, mqtt_connected: bool) -> None:
    for i, (name, raised) in enumerate(zip(FINGER_NAMES, states)):
        color = GREEN if raised else GRAY
        cv2.putText(frame, f"{name}: {raised}", (20, 40 + i * 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    status, color = ("MQTT connected", GREEN) if mqtt_connected else ("MQTT offline", RED)
    cv2.putText(frame, f"{status} | {fps:.0f} FPS", (20, frame.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


def main() -> None:
    settings = load_settings()

    camera = cv2.VideoCapture(settings.camera_index)
    if not camera.isOpened():
        print(f"Error: could not open camera {settings.camera_index}. "
              "Check CAMERA_INDEX in .env or close other apps using the webcam.")
        return

    publisher = MqttPublisher(
        host=settings.mqtt_host,
        port=settings.mqtt_port,
        topic=settings.mqtt_topic,
        client_id=settings.mqtt_client_id,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
    )
    publisher.start()

    stabilizer = StateStabilizer(settings.stable_frames)
    sent_states = None
    fps = 0.0
    last_frame_time = time.monotonic()

    try:
        with FingerDetector(settings.model_path,
                            settings.detection_confidence,
                            settings.tracking_confidence) as detector:
            print("Running. Press Esc or Q in the video window (or Ctrl+C) to quit.")
            while True:
                ok, frame = camera.read()
                if not ok:
                    print("Error: failed to read from camera.")
                    break

                # Mirror the image so it behaves like a mirror for the user.
                frame = cv2.flip(frame, 1)

                raw_states, landmarks = detector.detect(frame)
                states = stabilizer.update(raw_states)

                # Only send when something changed: real-time, but no flooding.
                if states != sent_states:
                    publisher.publish_states(states)
                    sent_states = states
                    print(f"Sent: {encode_states(states)}")

                if settings.show_preview:
                    now = time.monotonic()
                    fps = 0.9 * fps + 0.1 * (1.0 / max(now - last_frame_time, 1e-6))
                    last_frame_time = now

                    if landmarks is not None:
                        detector.draw(frame, landmarks)
                    draw_overlay(frame, states, fps, publisher.is_connected)
                    cv2.imshow("Finger Detector", frame)

                    key = cv2.waitKey(1) & 0xFF
                    if key in (ESC_KEY, ord("q")):
                        break
    except KeyboardInterrupt:
        pass
    finally:
        camera.release()
        cv2.destroyAllWindows()
        publisher.stop()


if __name__ == "__main__":
    main()
