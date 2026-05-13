/*
  Smart Weather Station MQTT simulator for ESP32.

  Arduino IDE libraries to install:
  - PubSubClient by Nick O'Leary

  Board:
  - ESP32 Dev Module, or your matching ESP32 board package.
*/

#include <WiFi.h>
#include <PubSubClient.h>

// For a Windows Mobile Hotspot demo, this is usually your laptop hotspot IP.
// If your hotspot shows a different gateway IP, put that value here.
const char* WIFI_SSID = "WeatherDemo";
const char* WIFI_PASSWORD = "weatherdemo123";

const char* MQTT_HOST = "192.168.137.1";
const uint16_t MQTT_PORT = 1883;
const char* MQTT_USERNAME = "weather_device";
const char* MQTT_PASSWORD = "strong_password";

const char* DEVICE_ID = "ws-esp32-001";
const char* FW_VERSION = "1.0.0-demo";

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

unsigned long lastPublishMs = 0;
uint32_t seq = 1;
uint32_t publishIntervalMs = 5000;

char dataTopic[80];
char statusTopic[80];
char cmdTopic[80];
char ackTopic[80];

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("Wi-Fi connected. ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void publishStatus(const char* status) {
  char payload[160];
  snprintf(
    payload,
    sizeof(payload),
    "{\"device_id\":\"%s\",\"status\":\"%s\",\"rssi_dbm\":%d,\"fw_version\":\"%s\"}",
    DEVICE_ID,
    status,
    WiFi.RSSI(),
    FW_VERSION
  );
  mqtt.publish(statusTopic, payload, true);
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  Serial.print("MQTT message on ");
  Serial.print(topic);
  Serial.print(": ");

  String body;
  for (unsigned int i = 0; i < length; i++) {
    body += (char)payload[i];
  }
  Serial.println(body);

  if (String(topic) == String(cmdTopic)) {
    if (body.indexOf("sample_interval") >= 0) {
      publishIntervalMs = 10000;
      Serial.println("Demo command received: sample interval changed to 10 seconds");
    } else if (body.indexOf("restart") >= 0) {
      Serial.println("Demo command received: restart requested");
    }
  }
}

void connectMqtt() {
  while (!mqtt.connected()) {
    Serial.print("Connecting to MQTT broker ");
    Serial.print(MQTT_HOST);
    Serial.print(":");
    Serial.println(MQTT_PORT);

    String clientId = String("weather-station-") + DEVICE_ID;
    if (mqtt.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD)) {
      Serial.println("MQTT connected");
      mqtt.subscribe(cmdTopic);
      mqtt.subscribe(ackTopic);
      publishStatus("online");
    } else {
      Serial.print("MQTT connect failed, rc=");
      Serial.print(mqtt.state());
      Serial.println(". Retrying in 2 seconds.");
      delay(2000);
    }
  }
}

void publishFakeReading() {
  float phase = seq * 0.15;
  float tempC = 29.0 + sin(phase) * 3.0;
  float humidity = 58.0 + cos(phase) * 8.0;
  float pressure = 1008.0 + sin(phase * 0.5) * 4.0;
  int rainRaw = 1800 + (int)(sin(phase * 0.8) * 500.0);
  bool rain = rainRaw < 1400;
  int batteryMv = 4100 - (seq % 100);
  int ts = 1710000000 + (millis() / 1000);

  char payload[420];
  snprintf(
    payload,
    sizeof(payload),
    "{\"schema\":\"weather.v1\",\"device_id\":\"%s\",\"seq\":%lu,\"ts\":%d,"
    "\"temp_c\":%.2f,\"humidity_pct\":%.2f,\"pressure_hpa\":%.2f,"
    "\"rain_raw\":%d,\"rain\":%s,\"rssi_dbm\":%d,\"battery_mv\":%d,"
    "\"fw_version\":\"%s\"}",
    DEVICE_ID,
    (unsigned long)seq,
    ts,
    tempC,
    humidity,
    pressure,
    rainRaw,
    rain ? "true" : "false",
    WiFi.RSSI(),
    batteryMv,
    FW_VERSION
  );

  bool ok = mqtt.publish(dataTopic, payload);
  Serial.print("Published reading #");
  Serial.print(seq);
  Serial.print(": ");
  Serial.println(ok ? payload : "publish failed");
  seq++;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  snprintf(dataTopic, sizeof(dataTopic), "weather/station/%s/data", DEVICE_ID);
  snprintf(statusTopic, sizeof(statusTopic), "weather/station/%s/status", DEVICE_ID);
  snprintf(cmdTopic, sizeof(cmdTopic), "weather/station/%s/cmd", DEVICE_ID);
  snprintf(ackTopic, sizeof(ackTopic), "weather/station/%s/ack", DEVICE_ID);

  connectWiFi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  mqtt.setBufferSize(512);
}

void loop() {
  connectWiFi();
  connectMqtt();
  mqtt.loop();

  if (millis() - lastPublishMs >= publishIntervalMs) {
    lastPublishMs = millis();
    publishFakeReading();
  }
}
