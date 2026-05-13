/*
  Smart Weather Station production ESP32 firmware.

  Hardware assumed:
  - ESP32 development board
  - BME280 over I2C for temperature, humidity, and pressure
  - Analog rain sensor module
  - Optional battery voltage divider connected to an ADC pin

  Arduino IDE libraries to install:
  - PubSubClient by Nick O'Leary
  - Adafruit BME280 Library by Adafruit
  - Adafruit Unified Sensor by Adafruit

  Board:
  - ESP32 Dev Module, or your matching ESP32 board package.
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_BME280.h>
#include <time.h>

// -----------------------------
// Demo network settings
// -----------------------------
const char* WIFI_SSID = "WeatherDemo";
const char* WIFI_PASSWORD = "weatherdemo123";

// Windows Mobile Hotspot usually uses 192.168.137.1 for the laptop.
const char* MQTT_HOST = "192.168.137.1";
const uint16_t MQTT_PORT = 1883;
const char* MQTT_USERNAME = "weather_device";
const char* MQTT_PASSWORD = "strong_password";

// -----------------------------
// Device identity
// -----------------------------
const char* DEVICE_ID = "ws-esp32-001";
const char* FW_VERSION = "1.0.0-prod";

// -----------------------------
// Sensor settings
// -----------------------------
const uint8_t I2C_SDA_PIN = 21;
const uint8_t I2C_SCL_PIN = 22;
const uint8_t BME280_ADDRESS = 0x76; // Common values: 0x76 or 0x77

const uint8_t RAIN_ANALOG_PIN = 34;
const int RAIN_ADC_DRY = 3000;
const int RAIN_ADC_WET = 1400;

const bool BATTERY_ENABLED = false;
const uint8_t BATTERY_ADC_PIN = 35;
const float ADC_REF_MV = 3300.0;
const float ADC_MAX = 4095.0;
const float BATTERY_DIVIDER_RATIO = 2.0; // Example: 100k + 100k divider

// -----------------------------
// Timing
// -----------------------------
uint32_t publishIntervalMs = 10000;
const uint32_t MQTT_RETRY_MS = 2500;
const uint32_t WIFI_RETRY_MS = 1000;

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
Adafruit_BME280 bme;

char dataTopic[80];
char statusTopic[80];
char cmdTopic[80];
char ackTopic[80];

uint32_t seq = 1;
unsigned long lastPublishMs = 0;
unsigned long lastMqttAttemptMs = 0;
bool bmeReady = false;

void buildTopics() {
  snprintf(dataTopic, sizeof(dataTopic), "weather/station/%s/data", DEVICE_ID);
  snprintf(statusTopic, sizeof(statusTopic), "weather/station/%s/status", DEVICE_ID);
  snprintf(cmdTopic, sizeof(cmdTopic), "weather/station/%s/cmd", DEVICE_ID);
  snprintf(ackTopic, sizeof(ackTopic), "weather/station/%s/ack", DEVICE_ID);
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(WIFI_RETRY_MS);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("Wi-Fi connected. ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void setupTime() {
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("Syncing NTP time");

  time_t now = time(nullptr);
  uint8_t attempts = 0;
  while (now < 1700000000 && attempts < 20) {
    delay(500);
    Serial.print(".");
    now = time(nullptr);
    attempts++;
  }
  Serial.println();

  if (now >= 1700000000) {
    Serial.print("NTP synced. Unix time: ");
    Serial.println((long)now);
  } else {
    Serial.println("NTP not synced yet. Firmware will retry in background.");
  }
}

void publishStatus(const char* status) {
  if (!mqtt.connected()) {
    return;
  }

  char payload[180];
  snprintf(
    payload,
    sizeof(payload),
    "{\"device_id\":\"%s\",\"status\":\"%s\",\"rssi_dbm\":%d,\"fw_version\":\"%s\",\"bme_ready\":%s}",
    DEVICE_ID,
    status,
    WiFi.RSSI(),
    FW_VERSION,
    bmeReady ? "true" : "false"
  );
  mqtt.publish(statusTopic, payload, true);
}

void handleCommand(String body) {
  if (body.indexOf("sample_interval") >= 0) {
    int valueIndex = body.indexOf("\"value\"");
    if (valueIndex >= 0) {
      int colonIndex = body.indexOf(":", valueIndex);
      if (colonIndex >= 0) {
        int seconds = body.substring(colonIndex + 1).toInt();
        if (seconds >= 2 && seconds <= 3600) {
          publishIntervalMs = (uint32_t)seconds * 1000UL;
        }
      }
    }
    Serial.print("Sample interval is now ");
    Serial.print(publishIntervalMs / 1000);
    Serial.println(" seconds");
  }

  if (body.indexOf("restart") >= 0) {
    Serial.println("Restart command received");
    delay(250);
    ESP.restart();
  }
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String body;
  body.reserve(length + 1);
  for (unsigned int i = 0; i < length; i++) {
    body += (char)payload[i];
  }

  Serial.print("MQTT message on ");
  Serial.print(topic);
  Serial.print(": ");
  Serial.println(body);

  if (String(topic) == String(cmdTopic)) {
    handleCommand(body);
  }
}

void connectMqtt() {
  if (mqtt.connected()) {
    return;
  }

  unsigned long nowMs = millis();
  if (nowMs - lastMqttAttemptMs < MQTT_RETRY_MS) {
    return;
  }
  lastMqttAttemptMs = nowMs;

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
    Serial.println(mqtt.state());
  }
}

int readRainRaw() {
  int total = 0;
  const int samples = 8;
  for (int i = 0; i < samples; i++) {
    total += analogRead(RAIN_ANALOG_PIN);
    delay(5);
  }
  return total / samples;
}

bool isRaining(int rainRaw) {
  return rainRaw <= RAIN_ADC_WET;
}

int readBatteryMv() {
  if (!BATTERY_ENABLED) {
    return -1;
  }

  int raw = analogRead(BATTERY_ADC_PIN);
  float pinMv = (raw / ADC_MAX) * ADC_REF_MV;
  return (int)(pinMv * BATTERY_DIVIDER_RATIO);
}

bool readingLooksValid(float tempC, float humidity, float pressureHpa, int rainRaw) {
  if (isnan(tempC) || isnan(humidity) || isnan(pressureHpa)) {
    return false;
  }
  if (tempC < -10.0 || tempC > 60.0) {
    return false;
  }
  if (humidity < 0.0 || humidity > 100.0) {
    return false;
  }
  if (pressureHpa < 800.0 || pressureHpa > 1100.0) {
    return false;
  }
  if (rainRaw < 0 || rainRaw > 4095) {
    return false;
  }
  return true;
}

void publishReading() {
  if (!bmeReady || !mqtt.connected()) {
    return;
  }

  float tempC = bme.readTemperature();
  float humidity = bme.readHumidity();
  float pressureHpa = bme.readPressure() / 100.0F;
  int rainRaw = readRainRaw();
  bool rain = isRaining(rainRaw);
  int batteryMv = readBatteryMv();
  time_t now = time(nullptr);

  if (now < 1700000000) {
    now = 1710000000 + (millis() / 1000);
  }

  if (!readingLooksValid(tempC, humidity, pressureHpa, rainRaw)) {
    Serial.println("Sensor reading failed local sanity check; skipping publish");
    publishStatus("sensor_error");
    return;
  }

  char batteryField[32] = "null";
  if (batteryMv >= 0) {
    snprintf(batteryField, sizeof(batteryField), "%d", batteryMv);
  }

  char payload[480];
  snprintf(
    payload,
    sizeof(payload),
    "{\"schema\":\"weather.v1\",\"device_id\":\"%s\",\"seq\":%lu,\"ts\":%ld,"
    "\"temp_c\":%.2f,\"humidity_pct\":%.2f,\"pressure_hpa\":%.2f,"
    "\"rain_raw\":%d,\"rain\":%s,\"rssi_dbm\":%d,\"battery_mv\":%s,"
    "\"fw_version\":\"%s\"}",
    DEVICE_ID,
    (unsigned long)seq,
    (long)now,
    tempC,
    humidity,
    pressureHpa,
    rainRaw,
    rain ? "true" : "false",
    WiFi.RSSI(),
    batteryField,
    FW_VERSION
  );

  bool ok = mqtt.publish(dataTopic, payload, false);
  Serial.print("Published reading #");
  Serial.print(seq);
  Serial.print(": ");
  Serial.println(ok ? payload : "publish failed");

  if (ok) {
    seq++;
  }
}

void setupSensors() {
  analogReadResolution(12);
  pinMode(RAIN_ANALOG_PIN, INPUT);
  if (BATTERY_ENABLED) {
    pinMode(BATTERY_ADC_PIN, INPUT);
  }

  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  bmeReady = bme.begin(BME280_ADDRESS);

  if (!bmeReady) {
    Serial.println("BME280 not found. Check wiring or try address 0x77.");
  } else {
    Serial.println("BME280 ready");
    bme.setSampling(
      Adafruit_BME280::MODE_NORMAL,
      Adafruit_BME280::SAMPLING_X2,
      Adafruit_BME280::SAMPLING_X16,
      Adafruit_BME280::SAMPLING_X1,
      Adafruit_BME280::FILTER_X16,
      Adafruit_BME280::STANDBY_MS_1000
    );
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  buildTopics();
  setupSensors();
  connectWiFi();
  setupTime();

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  mqtt.setBufferSize(768);
}

void loop() {
  connectWiFi();
  connectMqtt();
  mqtt.loop();

  if (millis() - lastPublishMs >= publishIntervalMs) {
    lastPublishMs = millis();
    publishReading();
  }
}
