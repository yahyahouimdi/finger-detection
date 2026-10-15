// Copy this file to "secrets.h" (same folder) and fill in your values.
// secrets.h is ignored by git, so your Wi-Fi password is never committed.
#pragma once

// Wi-Fi (the ESP32 only supports 2.4 GHz networks)
#define WIFI_SSID     "your-wifi-name"
#define WIFI_PASSWORD "your-wifi-password"

// MQTT broker: the IP of the computer running Mosquitto (same as MQTT_HOST in .env)
#define MQTT_HOST     "192.168.1.197"
#define MQTT_PORT     1883
// Must be the same as MQTT_TOPIC in finger_detector/.env
#define MQTT_TOPIC    "hand/gesture"
// Leave empty ("") if your broker allows anonymous connections
#define MQTT_USER     ""
#define MQTT_PASS     ""
