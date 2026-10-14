import cv2
import paho.mqtt.client as mqtt

# mediapipe import compatibility: some builds expose `solutions` on the package,
# others provide `mediapipe.solutions` as a submodule. Try both.
try:
    import mediapipe as mp
    if hasattr(mp, "solutions"):
        solutions = mp.solutions
    else:
        from mediapipe import solutions
except Exception:
    from mediapipe import solutions


broker = "192.168.1.197"  # IP of broker
port = 1883

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # create MediaPipe objects here so we can close them cleanly
    mp_hands = solutions.hands
    hands = mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )
    mp_draw = solutions.drawing_utils

    client = mqtt.Client()
    client.connect(broker, port, 60)
    client.loop_start()

    try:
        while True:
            success, frame = cap.read()
            if not success:
                print("Failed to read from camera.")
                break

            frame = cv2.flip(frame, 1)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            results = hands.process(rgb)

            a = b = c = d = e = 0

            if results.multi_hand_landmarks:
                for handLms in results.multi_hand_landmarks:
                    lm = handLms.landmark

                    # Thumb
                    if lm[4].x < lm[3].x:
                        a = 1

                    # Index
                    if lm[8].y < lm[6].y:
                        b = 1

                    # Middle
                    if lm[12].y < lm[10].y:
                        c = 1

                    # Ring
                    if lm[16].y < lm[14].y:
                        d = 1

                    # Pinky
                    if lm[20].y < lm[18].y:
                        e = 1

                    mp_draw.draw_landmarks(
                        frame,
                        handLms,
                        mp_hands.HAND_CONNECTIONS
                    )

            print(f"a={a}, b={b}, c={c}, d={d}, e={e}")
            data = f"{a},{b},{c},{d},{e}"

            client.publish("hand/gesture", data)

            print("Sent:", data)
            cv2.putText(
                frame,
                f"{a} {b} {c} {d} {e}",
                (20,50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0,255,0),
                2
            )

            cv2.imshow("Hand Tracking", frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:
            pass
        try:
            hands.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()





    