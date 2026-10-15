// Hand LEDs - ESP32
// Receives "a,b,c,d,e" (thumb, index, middle, ring, pinky; 1 = raised) over MQTT
// and lights one LED per raised finger.
//
// Libraries: "PubSubClient" by Nick O'Leary (Library Manager).
// Settings:  copy secrets.example.h to secrets.h and fill it in.

#include <WiFi.h>
#include <PubSubClient.h>
#include "secrets.h"

const int NUM_LEDS = 5;
// thumb, index, middle, ring, pinky. These GPIOs are safe to use as outputs.
const uint8_t LED_PINS[NUM_LEDS] = {25, 26, 27, 32, 33};
const char* FINGER_NAMES[NUM_LEDS] = {"thumb", "index", "middle", "ring", "pinky"};

const unsigned long MQTT_RETRY_MS = 2000;

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
unsigned long lastMqttAttempt = 0;

void setAllLeds(int value) {
  for (int i = 0; i < NUM_LEDS; i++) {
    digitalWrite(LED_PINS[i], value);
  }
}

// Called by PubSubClient every time a message arrives on MQTT_TOPIC.
void onMessage(char* topic, byte* payload, unsigned int length) {
  int values[NUM_LEDS];
  int count = 0;

  // Keep only the 0/1 digits: "1,0,1,0,0" -> {1,0,1,0,0}
  for (unsigned int i = 0; i < length; i++) {
    char c = (char)payload[i];
    if (c == '0' || c == '1') {
      if (count == NUM_LEDS) {
        count++;  // too many values
        break;
      }
      values[count++] = c - '0';
    } else if (c != ',' && c != ' ' && c != '\r' && c != '\n') {
      count = -1;  // unexpected character
      break;
    }
  }

  if (count != NUM_LEDS) {
    Serial.print("Ignored invalid message: ");
    Serial.write(payload, length);
    Serial.println();
    return;
  }

  Serial.print("Received:");
  for (int i = 0; i < NUM_LEDS; i++) {
    digitalWrite(LED_PINS[i], values[i] ? HIGH : LOW);
    Serial.printf(" %s=%d", FINGER_NAMES[i], values[i]);
  }
  Serial.println();
}

void connectWifi() {
  Serial.printf("Connecting to Wi-Fi \"%s\"", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\nWi-Fi connected, ESP32 IP: %s\n", WiFi.localIP().toString().c_str());
}

bool connectMqtt() {
  // A unique client ID, built from the chip's MAC address.
  String clientId = "esp32-hand-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  Serial.printf("Connecting to MQTT %s:%d ... ", MQTT_HOST, MQTT_PORT);

  bool ok;
  if (strlen(MQTT_USER) > 0) {
    ok = mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASS);
  } else {
    ok = mqtt.connect(clientId.c_str());
  }

  if (!ok) {
    Serial.printf("failed (state %d), retrying in %lu s\n", mqtt.state(), MQTT_RETRY_MS / 1000);
    return false;
  }

  Serial.println("connected");
  mqtt.subscribe(MQTT_TOPIC);
  Serial.printf("Subscribed to \"%s\"\n", MQTT_TOPIC);
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(200);

  for (int i = 0; i < NUM_LEDS; i++) {
    pinMode(LED_PINS[i], OUTPUT);
  }

  // Quick self-test: all LEDs on for half a second, to check the wiring.
  setAllLeds(HIGH);
  delay(500);
  setAllLeds(LOW);

  connectWifi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMessage);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    setAllLeds(LOW);
    connectWifi();
  }

  if (!mqtt.connected()) {
    // Retry without blocking the loop with long delays.
    unsigned long now = millis();
    if (now - lastMqttAttempt >= MQTT_RETRY_MS) {
      lastMqttAttempt = now;
      connectMqtt();
    }
    return;
  }

  mqtt.loop();  // receives messages and calls onMessage()
}
