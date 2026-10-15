# Step-by-step guide: Broker, Arduino IDE and ESP32

This guide takes you from nothing to "LEDs follow my fingers". Follow the parts in order.

- [Part 1 — Set up the MQTT broker on the PC](#part-1--set-up-the-mqtt-broker-on-the-pc)
- [Part 2 — Install and prepare the Arduino IDE](#part-2--install-and-prepare-the-arduino-ide)
- [Part 3 — Wire the LEDs](#part-3--wire-the-leds)
- [Part 4 — Configure and upload the sketch](#part-4--configure-and-upload-the-sketch)
- [Part 5 — Run everything together](#part-5--run-everything-together)
- [Part 6 — Troubleshooting](#part-6--troubleshooting)

---

## Part 1 — Set up the MQTT broker on the PC

The **broker** is the "post office" that receives messages from the Python program and delivers them to the ESP32. We use **Mosquitto**.

### 1.1 Install Mosquitto

1. Download the Windows 64-bit installer from <https://mosquitto.org/download/>.
2. Run it and keep the defaults. It installs to `C:\Program Files\mosquitto` and creates a Windows service that starts automatically.

### 1.2 Allow other devices to connect

By default, Mosquitto 2.x **only accepts connections from the same PC**. The ESP32 is a different device, so it would be refused.

1. Open the Start menu, type **Notepad**, right-click it and choose **Run as administrator**.
2. In Notepad, click **File → Open** and open `C:\Program Files\mosquitto\mosquitto.conf` (set the file type to "All files").
3. Add these two lines at the very end of the file and save:

   ```
   listener 1883 0.0.0.0
   allow_anonymous true
   ```

   - `listener 1883 0.0.0.0` tells Mosquitto to listen on port 1883 on every network card, not only "localhost".
   - `allow_anonymous true` lets devices connect without a username or password. This is fine on your home network. Don't do it on a public network (see the security note in the report).

4. Open **PowerShell as Administrator** and run:

   ```powershell
   Restart-Service mosquitto
   New-NetFirewallRule -DisplayName "Mosquitto MQTT" -Direction Inbound -Protocol TCP -LocalPort 1883 -Action Allow
   ```

5. Make sure Windows treats your Wi-Fi as a **Private** network: **Settings → Network & Internet → Wi-Fi → (your network) → Network profile type → Private**.

### 1.3 Find the PC's IP address

In PowerShell, run `ipconfig`. Look at the **Wireless LAN adapter Wi-Fi** section and note the **IPv4 Address**, for example `192.168.1.197`.

> ⚠️ This IP can change when the PC reconnects to Wi-Fi. If the project suddenly stops working, check it again.
> To keep it fixed, set up a "DHCP reservation" for your PC in your router's settings.

Put this IP in **both** places:
- `finger_detector/.env` → `MQTT_HOST=...`
- `esp32/hand_leds/secrets.h` → `#define MQTT_HOST "..."`

### 1.4 Test the broker

Open two PowerShell windows.

Window 1 listens:
```powershell
& "C:\Program Files\mosquitto\mosquitto_sub.exe" -h <YOUR_PC_IP> -t hand/gesture -v
```

Window 2 sends:
```powershell
& "C:\Program Files\mosquitto\mosquitto_pub.exe" -h <YOUR_PC_IP> -t hand/gesture -m "1,1,0,0,0"
```

If window 1 prints `hand/gesture 1,1,0,0,0`, the broker works ✅. Use the real IP here, not `localhost`, so that you are also testing the network setup.

---

## Part 2 — Install and prepare the Arduino IDE

### 2.1 Install the Arduino IDE

Download **Arduino IDE 2.x** from <https://www.arduino.cc/en/software> and install it.

### 2.2 Add ESP32 support

The Arduino IDE doesn't know about the ESP32 out of the box. You need to add Espressif's boards package.

1. Open **File → Preferences**.
2. In **Additional boards manager URLs**, paste:
   ```
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```
3. Click **OK**.
4. Open **Tools → Board → Boards Manager…** (or click the second icon in the left sidebar).
5. Search for **esp32** and install **"esp32 by Espressif Systems"**. The download is large, so it takes a few minutes.

### 2.3 Install the MQTT library

1. Open **Sketch → Include Library → Manage Libraries…** (or click the third icon in the left sidebar).
2. Search for **PubSubClient** and install **"PubSubClient by Nick O'Leary"**.

`WiFi.h` comes with the ESP32 package, so you don't need to install anything else.

### 2.4 Connect the ESP32 and select the port

1. Plug the ESP32 into the PC with a USB cable. It must be a **data** cable: some cables only charge.
2. Open **Device Manager → Ports (COM & LPT)**. You should see something like `Silicon Labs CP210x … (COM5)` or `USB-SERIAL CH340 (COM5)`.
   - If you only see an "Unknown device", install the USB driver for your board's chip:
     - CP210x: <https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers>
     - CH340: search for "CH340 driver" from WCH (wch-ic.com)
3. In the Arduino IDE:
   - **Tools → Board → esp32 → ESP32 Dev Module** (this fits most ESP32-WROOM-32 / DevKit V1 boards)
   - **Tools → Port →** the COM port you saw in Device Manager

### 2.5 (Optional) Test with "Blink"

**File → Examples → 01.Basics → Blink**, then click **Upload** (→). On most DevKit boards, the small blue LED (GPIO 2) starts blinking. This confirms that uploading works before you try the real project.

---

## Part 3 — Wire the LEDs

### 3.1 How an LED is connected

An LED has two legs:
- **Long leg = anode (+)**: goes toward the ESP32 pin
- **Short leg = cathode (−)**: goes to GND. The side of the LED's plastic rim is also flat on this side.

Each LED **must** have a resistor in series (220 Ω to 330 Ω). Without one, the LED draws too much current and can damage itself or the ESP32 pin.

```
ESP32 GPIO ──── [220 Ω] ────▶|──── GND
                           LED
                      (long)  (short)
```

### 3.2 Connections

| Finger | ESP32 pin | Wiring |
|--------|-----------|--------|
| Thumb  | GPIO 25 (`D25`) | D25 → 220 Ω → LED 1 long leg; LED 1 short leg → GND |
| Index  | GPIO 26 (`D26`) | D26 → 220 Ω → LED 2 long leg; short leg → GND |
| Middle | GPIO 27 (`D27`) | D27 → 220 Ω → LED 3 long leg; short leg → GND |
| Ring   | GPIO 32 (`D32`) | D32 → 220 Ω → LED 4 long leg; short leg → GND |
| Pinky  | GPIO 33 (`D33`) | D33 → 220 Ω → LED 5 long leg; short leg → GND |

Connect one **GND** pin of the ESP32 to the breadboard's blue (−) rail. Then connect all 5 short legs to that rail.

```
                 ┌─────────────────┐
                 │      ESP32      │
                 │                 │
   LED1 ◀─220Ω───┤ D25             │
   LED2 ◀─220Ω───┤ D26             │
   LED3 ◀─220Ω───┤ D27             │
   LED4 ◀─220Ω───┤ D32             │
   LED5 ◀─220Ω───┤ D33             │
                 │             GND ├────── breadboard (−) rail ── all LED short legs
                 └──────┬──────────┘
                        USB → PC
```

> Why these pins? Some ESP32 pins have special roles at boot (GPIO 0, 2, 12, 15) or can only be inputs (GPIO 34 to 39). Pins 25, 26, 27, 32 and 33 are plain outputs with no surprises.
> If you change pins, update `LED_PINS` in `hand_leds.ino`.

---

## Part 4 — Configure and upload the sketch

### 4.1 Create `secrets.h`

1. Go to the `esp32/hand_leds/` folder.
2. Copy `secrets.example.h` and rename the copy to **`secrets.h`**. It must be in the same folder as `hand_leds.ino`.
3. Edit `secrets.h`:

   ```cpp
   #define WIFI_SSID     "MyHomeWifi"        // your Wi-Fi name (2.4 GHz!)
   #define WIFI_PASSWORD "my-wifi-password"
   #define MQTT_HOST     "192.168.1.197"     // the PC IP from Part 1.3
   #define MQTT_PORT     1883
   #define MQTT_TOPIC    "hand/gesture"      // same as MQTT_TOPIC in .env
   #define MQTT_USER     ""
   #define MQTT_PASS     ""
   ```

`secrets.h` is listed in `.gitignore`, so your Wi-Fi password is never pushed to GitHub.

### 4.2 Open and upload

1. In the Arduino IDE: **File → Open…** → `esp32/hand_leds/hand_leds.ino`.
   `secrets.h` should appear as a second tab. The Arduino IDE requires the folder name to match the `.ino` name, and here it already does.
2. Check **Tools → Board = ESP32 Dev Module** and **Tools → Port = your COM port**.
3. Click **Verify** (✓) to compile. It should finish with "Done compiling".
4. Click **Upload** (→).
   - If it gets stuck on `Connecting........_____`, **hold the BOOT button** on the ESP32 until the upload starts, then release it.

### 4.3 Check the Serial Monitor

1. Open **Tools → Serial Monitor** and set the speed (bottom right) to **115200 baud**.
2. Press the **EN/RST** button on the ESP32 to restart it. You should see:

   ```
   Connecting to Wi-Fi "MyHomeWifi"......
   Wi-Fi connected, ESP32 IP: 192.168.1.50
   Connecting to MQTT 192.168.1.197:1883 ... connected
   Subscribed to "hand/gesture"
   ```

At startup, all 5 LEDs turn on for half a second. This is a wiring self-test, so if one LED stays dark, check that LED's wiring.

### 4.4 Test the LEDs without the camera

From PowerShell on the PC:

```powershell
& "C:\Program Files\mosquitto\mosquitto_pub.exe" -h <YOUR_PC_IP> -t hand/gesture -m "1,0,1,0,1"
```

LEDs 1, 3 and 5 should turn on, and the Serial Monitor prints `Received: thumb=1 index=0 middle=1 ring=0 pinky=1`.

---

## Part 5 — Run everything together

1. Make sure Mosquitto is running: `Get-Service mosquitto` should show `Running`.
2. Power the ESP32 (USB). Wait for "Subscribed" in the Serial Monitor.
3. On the PC:

   ```powershell
   cd finger_detector
   ..\.venv\Scripts\Activate.ps1
   python main.py
   ```

4. Show your hand to the camera, palm facing it and fingers pointing up. Raise and lower fingers, and the LEDs follow 🎉
5. Press **Esc** or **Q** in the video window to quit. All LEDs turn off.

If the Python program crashes or the PC loses the network, the broker sends the "last will" message `0,0,0,0,0`, so the LEDs turn off by themselves.

---

## Part 6 — Troubleshooting

### Upload problems

| Symptom | Fix |
|---------|-----|
| No COM port appears | Use a data USB cable, install the CP210x or CH340 driver, or try another USB port |
| `Failed to connect to ESP32: Timed out… Connecting...` | Hold **BOOT** while uploading. Close the Serial Monitor in other programs |
| `secrets.h: No such file or directory` | You didn't create `secrets.h` (Part 4.1), or it's in the wrong folder |
| `PubSubClient.h: No such file or directory` | Install the PubSubClient library (Part 2.3) |

### Serial Monitor shows…

| Message | Meaning / fix |
|---------|---------------|
| Unreadable characters | Set the baud rate to **115200** |
| Dots forever after `Connecting to Wi-Fi` | Wrong SSID or password, or a 5 GHz-only network. The ESP32 only supports **2.4 GHz** |
| `failed (state -2)` | It can't reach the broker: wrong `MQTT_HOST`, missing `listener 1883 0.0.0.0`, firewall blocking port 1883, or the PC is on a different network |
| `failed (state 5)` | The broker requires a login: set `MQTT_USER` / `MQTT_PASS`, or `allow_anonymous true` |
| `Ignored invalid message` | Something sent a message that isn't 5 comma-separated 0/1 values |

### LEDs

| Symptom | Fix |
|---------|-----|
| One LED never lights, even during the startup self-test | The LED is backwards (swap its legs), the resistor isn't connected, or it's on the wrong pin |
| LEDs work with `mosquitto_pub` but not with the camera | Check that `MQTT_HOST` and `MQTT_TOPIC` in `.env` match `secrets.h`. Look for "MQTT connected" in the video window |
| LEDs flicker | Increase `STABLE_FRAMES` in `.env`, improve the lighting, and keep the whole hand in view |
