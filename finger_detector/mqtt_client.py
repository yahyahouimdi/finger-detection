"""MQTT connection: sends the 5 finger states to the broker.

The ESP32 subscribes to the same topic and turns its LEDs on/off.
"""

import paho.mqtt.client as mqtt

ALL_OFF = "0,0,0,0,0"


def encode_states(states: tuple[int, ...]) -> str:
    """(1, 0, 1, 0, 0) -> "1,0,1,0,0" """
    return ",".join(str(s) for s in states)


class MqttPublisher:
    def __init__(
        self,
        host: str,
        port: int,
        topic: str,
        client_id: str,
        username: str | None = None,
        password: str | None = None,
    ):
        self.host = host
        self.port = port
        self.topic = topic
        self._last_payload = ALL_OFF

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        if username:
            self._client.username_pw_set(username, password)

        # "Last will": if this program crashes or loses the network, the broker
        # publishes this message for us, so the LEDs don't stay stuck on.
        self._client.will_set(topic, ALL_OFF, qos=1, retain=True)

        self._client.reconnect_delay_set(min_delay=1, max_delay=10)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    @property
    def is_connected(self) -> bool:
        return self._client.is_connected()

    def start(self) -> None:
        """Connect in the background. Never blocks or crashes if the broker is down;
        paho keeps retrying automatically."""
        print(f"[MQTT] Connecting to {self.host}:{self.port} ...")
        self._client.connect_async(self.host, self.port, keepalive=30)
        self._client.loop_start()

    def publish_states(self, states: tuple[int, ...]) -> None:
        payload = encode_states(states)
        self._last_payload = payload
        # retain=True: the broker remembers the last value, so an ESP32 that
        # (re)connects immediately gets the current state.
        self._client.publish(self.topic, payload, qos=0, retain=True)

    def stop(self) -> None:
        """Turn all LEDs off, then disconnect cleanly."""
        if self.is_connected:
            info = self._client.publish(self.topic, ALL_OFF, qos=1, retain=True)
            try:
                info.wait_for_publish(timeout=2)
            except (ValueError, RuntimeError):
                pass
        self._client.disconnect()
        self._client.loop_stop()
        print("[MQTT] Disconnected.")

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"[MQTT] Connection refused: {reason_code}")
            return
        print(f"[MQTT] Connected to {self.host}:{self.port}, topic '{self.topic}'")
        # Re-send the current state so the ESP32 is in sync after a reconnect.
        client.publish(self.topic, self._last_payload, qos=0, retain=True)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            print(f"[MQTT] Connection lost ({reason_code}), retrying ...")
