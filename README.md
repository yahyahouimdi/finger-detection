# Hand Finger LEDs ✋💡

Raise your fingers in front of a webcam, and 5 LEDs on an ESP32 light up to match, in real time.

```
 ┌──────────┐    ┌──────────────────────┐   MQTT    ┌──────────────┐   MQTT   ┌───────────┐
 │  Webcam  │───▶│  PC: Python program  │──────────▶│   Mosquitto  │─────────▶│   ESP32   │──▶ 5 LEDs
 └──────────┘    │  MediaPipe finds the │ "1,0,1,0,0"│   (broker)   │          │ (Wi-Fi)   │
                 │  hand + 5 fingers    │           └──────────────┘          └───────────┘
                 └──────────────────────┘
```

| Finger | Variable | ESP32 pin |
|--------|----------|-----------|
| Thumb  | a        | GPIO 25   |
| Index  | b        | GPIO 26   |
| Middle | c        | GPIO 27   |
| Ring   | d        | GPIO 32   |
| Pinky  | e        | GPIO 33   |

Message sent on topic `hand/gesture`: `a,b,c,d,e` where `1` = raised and `0` = down.
For example, `0,1,1,0,0` is a "peace" sign, so only the index and middle LEDs turn on.

## Project structure

```
.
├── finger_detector/            # Python program (runs on the PC)
│   ├── main.py                 # Entry point: camera loop, sends changes over MQTT
│   ├── finger_detector.py      # MediaPipe hand detection + finger up/down logic
│   ├── mqtt_client.py          # MQTT connection (publish, reconnect, last will)
│   ├── config.py               # Reads settings from .env
│   ├── .env.example            # Template for your settings (copy to .env)
│   ├── requirements.txt
│   └── models/                 # Hand model, downloaded automatically on first run
├── esp32/hand_leds/            # Arduino sketch (runs on the ESP32)
│   ├── hand_leds.ino           # Wi-Fi + MQTT + LEDs
│   └── secrets.example.h       # Template for Wi-Fi/MQTT settings (copy to secrets.h)
└── docs/
    ├── ESP32_ARDUINO_GUIDE.md  # Step-by-step: Arduino IDE, wiring, upload, broker
    └── REPORT.md               # Full explanation of the project, for beginners
```

## What you need

- A PC with a webcam and Python 3.10 or newer (tested with Python 3.14)
- An ESP32 dev board (e.g. ESP32 DevKit V1 / ESP32-WROOM-32) and a USB data cable
- 5 LEDs, 5 resistors (220 Ω to 330 Ω), a breadboard and jumper wires
- A 2.4 GHz Wi-Fi network shared by the PC and the ESP32
- [Mosquitto](https://mosquitto.org/download/), the MQTT broker, installed on the PC

## Quick start

### 1. MQTT broker (one time)

Mosquitto 2.x only accepts connections from the PC it runs on by default, which means it **refuses the ESP32**.
Open `C:\Program Files\mosquitto\mosquitto.conf` as Administrator and add at the end:

```
listener 1883 0.0.0.0
allow_anonymous true
```

Then restart Mosquitto and open the firewall port. Run this in PowerShell **as Administrator**:

```powershell
Restart-Service mosquitto
New-NetFirewallRule -DisplayName "Mosquitto MQTT" -Direction Inbound -Protocol TCP -LocalPort 1883 -Action Allow
```

Find your PC's IP with `ipconfig`: use the "IPv4 Address" of your Wi-Fi adapter.
More details are in the [guide](docs/ESP32_ARDUINO_GUIDE.md#part-1--set-up-the-mqtt-broker-on-the-pc).

### 2. Python program (PC)

```powershell
cd finger_detector
python -m venv ..\.venv
..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env       # then edit .env: set MQTT_HOST to your PC's IP
python main.py
```

A window opens and shows your hand and the 5 finger states. Press **Esc** or **Q** to quit. Quitting also turns all the LEDs off.

### 3. ESP32

1. Wire the LEDs (see the [wiring section](docs/ESP32_ARDUINO_GUIDE.md#part-3--wire-the-leds)).
2. In `esp32/hand_leds/`, copy `secrets.example.h` to `secrets.h` and fill in your Wi-Fi name, Wi-Fi password and the PC's IP.
3. Open `hand_leds.ino` in the Arduino IDE, install the **esp32** boards package and the **PubSubClient** library, and upload.

The full click-by-click instructions are in **[docs/ESP32_ARDUINO_GUIDE.md](docs/ESP32_ARDUINO_GUIDE.md)**.

## Configuration (`finger_detector/.env`)

| Variable | Default | Meaning |
|----------|---------|---------|
| `MQTT_HOST` | `192.168.1.197` | IP of the PC running Mosquitto |
| `MQTT_PORT` | `1883` | MQTT port |
| `MQTT_TOPIC` | `hand/gesture` | Must match `MQTT_TOPIC` in `secrets.h` |
| `MQTT_CLIENT_ID` | `finger-detector-pc` | Name of this program on the broker |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | empty | Only if your broker requires a login |
| `CAMERA_INDEX` | `0` | Which webcam to use |
| `SHOW_PREVIEW` | `true` | Show the video window |
| `DETECTION_CONFIDENCE` | `0.7` | How sure MediaPipe must be that it sees a hand (0 to 1) |
| `TRACKING_CONFIDENCE` | `0.7` | How sure it must be to keep tracking it (0 to 1) |
| `STABLE_FRAMES` | `2` | Frames a new state must last before it is sent (removes flicker) |

## Testing without the ESP32

Watch what the PC sends:

```powershell
& "C:\Program Files\mosquitto\mosquitto_sub.exe" -h localhost -t hand/gesture -v
```

Test the ESP32 without the camera:

```powershell
& "C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t hand/gesture -m "1,0,1,0,1" -r
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `MQTT offline` in the video window | Wrong `MQTT_HOST` in `.env`, or Mosquitto isn't running (`Get-Service mosquitto`) |
| ESP32 shows `failed (state -2)` | It can't reach the broker: check the `listener` line in `mosquitto.conf`, the firewall rule, and the IP in `secrets.h` |
| ESP32 never connects to Wi-Fi | The network must be 2.4 GHz. Check the SSID and password (they are case-sensitive) |
| `could not open camera` | Close other apps that use the webcam, or try `CAMERA_INDEX=1` |
| Fingers flicker | Increase `STABLE_FRAMES` to 3, improve the lighting, and keep the whole hand in view |
| Thumb is wrong | Show your palm (or the back of your hand) flat to the camera, fingers pointing up |

## Documentation

- 📘 **[Step-by-step ESP32 / Arduino IDE guide](docs/ESP32_ARDUINO_GUIDE.md)**
- 📗 **[Full project report](docs/REPORT.md)**: how computer vision, MediaPipe, MQTT and the ESP32 work, explained for beginners
