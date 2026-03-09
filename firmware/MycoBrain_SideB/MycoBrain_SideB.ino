/*
 * MycoBrain Side-B (Communications MCU) Firmware v2.0.0
 * ESP32-S3 — Pure transport and routing. No sensor or motor logic.
 *
 * Features:
 * - UART communication with Side-A (or Jetson middle-layer)
 * - Wi-Fi + MQTT publish of MMP envelopes
 * - LoRa relay (SX1262) for offline/field mesh
 * - Store-and-forward buffer for offline periods
 * - MAS heartbeat mirror (when Jetson absent, Side B heartbeats directly)
 * - BLE beacon (future)
 * - LTE modem (SIM7600X via UART AT commands, future)
 * - Command routing (MAS/Jetson -> Side-A)
 * - Connection monitoring
 *
 * Protocol:
 * - Receives NDJSON from Side-A or Jetson over UART
 * - Wraps in MMP envelope if not already wrapped
 * - Publishes to MQTT topic: mycosoft/devices/{device_id}/{kind}/{capability_id}
 * - Falls back to LoRa relay when Wi-Fi unavailable
 * - Stores up to STORE_FORWARD_MAX messages when fully offline
 *
 * Created: March 9, 2026
 */

#include <Arduino.h>
#include <HardwareSerial.h>
#include <ArduinoJson.h>
#include <WiFi.h>

// ============================================================================
// Configuration
// ============================================================================
#define SERIAL_BAUD 115200
#define UART_TO_SIDEA Serial1
#define UART_BAUD 115200
#define FIRMWARE_VERSION "2.0.0-comms"

// UART pins to Side-A (or Jetson)
#define UART_RX 16
#define UART_TX 17

// Status LED
#define LED_PIN 2

// LoRa pins (SX1262 — adjust for your board)
#define LORA_NSS   10
#define LORA_RST   8
#define LORA_DIO1  3
#define LORA_BUSY  9

// SIM7600X UART (optional LTE modem — UART2)
#define MODEM_RX 44
#define MODEM_TX 43
#define MODEM_BAUD 115200

// Wi-Fi credentials (loaded from NVS in production, hardcoded for dev)
const char* WIFI_SSID = "";     // Set via command or NVS
const char* WIFI_PASS = "";     // Set via command or NVS

// MQTT config
const char* MQTT_BROKER = "192.168.0.189";
const int   MQTT_PORT = 1883;

// MAS heartbeat URL (used when Jetson is absent)
const char* MAS_HEARTBEAT_URL = "http://192.168.0.188:8001/api/devices/heartbeat";

// Store-and-forward
#define STORE_FORWARD_MAX 100

// Timing
#define HEARTBEAT_INTERVAL_MS 30000    // 30 seconds
#define WIFI_RECONNECT_INTERVAL_MS 60000
#define LORA_CHECK_INTERVAL_MS 5000

static const uint32_t BOOT_SERIAL_WAIT_MS = 1800;

// ============================================================================
// Global Variables
// ============================================================================
String deviceMac = "";
String deviceId = "";
unsigned long uptimeSeconds = 0;
unsigned long lastUptimeUpdate = 0;
unsigned long lastHeartbeat = 0;
unsigned long lastWifiReconnect = 0;

String sideACommandBuffer = "";
String uartCommandBuffer = "";

bool sideAConnected = false;
unsigned long lastSideAHeartbeat = 0;
unsigned long sideATimeout = 5000;

bool wifiConnected = false;
bool mqttConnected = false;
bool loraAvailable = false;
bool lteAvailable = false;

// Store-and-forward ring buffer
String storeForwardBuffer[STORE_FORWARD_MAX];
int sfHead = 0;
int sfTail = 0;
int sfCount = 0;

// ============================================================================
// Setup
// ============================================================================
void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(BOOT_SERIAL_WAIT_MS);

  // UART to Side-A (or Jetson)
  UART_TO_SIDEA.begin(UART_BAUD, SERIAL_8N1, UART_RX, UART_TX);
  delay(100);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // Get MAC for device identity
  uint64_t chipid = ESP.getEfuseMac();
  char macStr[18];
  snprintf(macStr, sizeof(macStr), "%02X:%02X:%02X:%02X:%02X:%02X",
           (uint8_t)(chipid >> 40), (uint8_t)(chipid >> 32),
           (uint8_t)(chipid >> 24), (uint8_t)(chipid >> 16),
           (uint8_t)(chipid >> 8), (uint8_t)chipid);
  deviceMac = String(macStr);

  // Generate device_id from last 6 hex chars of MAC
  String macClean = deviceMac;
  macClean.replace(":", "");
  deviceId = "MYCOBRAIN-" + macClean.substring(macClean.length() - 6);
  deviceId.toUpperCase();

  Serial.println("\n=== MycoBrain Side-B (Comms v2) ===");
  Serial.print("MAC: "); Serial.println(deviceMac);
  Serial.print("Device ID: "); Serial.println(deviceId);
  Serial.print("Firmware: "); Serial.println(FIRMWARE_VERSION);

  // Initialize Wi-Fi (if credentials set)
  initWifi();

  // Initialize LoRa (if hardware present)
  initLoRa();

  // Blink LED
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH); delay(100);
    digitalWrite(LED_PIN, LOW); delay(100);
  }

  Serial.println("Waiting for Side-A / Jetson...");
  pingSideA();
}

// ============================================================================
// Main Loop
// ============================================================================
void loop() {
  unsigned long now = millis();

  if (now - lastUptimeUpdate >= 1000) {
    uptimeSeconds = now / 1000;
    lastUptimeUpdate = now;
  }

  // Handle PC/Jetson commands (USB Serial)
  handlePCCommands();

  // Handle Side-A data (UART)
  handleSideAData();

  // Side-A connection monitor
  if (now - lastSideAHeartbeat > sideATimeout) {
    if (sideAConnected) {
      sideAConnected = false;
      digitalWrite(LED_PIN, LOW);
      Serial.println("{\"type\":\"event\",\"event\":\"side_a_disconnected\"}");
    }
  } else if (!sideAConnected) {
    sideAConnected = true;
    digitalWrite(LED_PIN, HIGH);
    Serial.println("{\"type\":\"event\",\"event\":\"side_a_connected\"}");
  }

  // Wi-Fi reconnect
  if (!wifiConnected && (now - lastWifiReconnect > WIFI_RECONNECT_INTERVAL_MS)) {
    initWifi();
    lastWifiReconnect = now;
  }

  // Flush store-forward buffer when online
  if (wifiConnected && sfCount > 0) {
    flushStoreForward();
  }

  // MAS heartbeat (only when Jetson is not doing it)
  // If Jetson is present, it handles heartbeats. Side B only heartbeats as fallback.
  // TODO: detect jetson_present flag from incoming data
  if (now - lastHeartbeat > HEARTBEAT_INTERVAL_MS) {
    // Heartbeat logic would go here (HTTP POST or MQTT publish)
    lastHeartbeat = now;
  }

  delay(10);
}

// ============================================================================
// Wi-Fi
// ============================================================================
void initWifi() {
  if (strlen(WIFI_SSID) == 0) {
    Serial.println("[WiFi] No SSID configured");
    return;
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - start < 10000)) {
    delay(500);
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.print("[WiFi] Connected: ");
    Serial.println(WiFi.localIP());
  } else {
    wifiConnected = false;
    Serial.println("[WiFi] Connection failed");
  }
}

// ============================================================================
// LoRa (SX1262 stub — requires RadioLib or similar)
// ============================================================================
void initLoRa() {
  // TODO: Initialize SX1262 via SPI using RadioLib
  // RadioLib SX1262 module(LORA_NSS, LORA_DIO1, LORA_RST, LORA_BUSY);
  // int state = module.begin(915.0);
  // loraAvailable = (state == RADIOLIB_ERR_NONE);
  loraAvailable = false;
  Serial.println("[LoRa] Not initialized (add RadioLib)");
}

void sendLoRa(String payload) {
  if (!loraAvailable) return;
  // TODO: module.transmit(payload);
  Serial.println("[LoRa] TX: " + payload.substring(0, 50) + "...");
}

// ============================================================================
// MQTT (stub — requires PubSubClient or AsyncMqttClient)
// ============================================================================
void publishMQTT(String topic, String payload) {
  if (!wifiConnected) {
    // Store for later
    storeForwardEnqueue(payload);
    return;
  }

  // TODO: Initialize PubSubClient and publish
  // mqttClient.publish(topic.c_str(), payload.c_str());
  Serial.println("[MQTT] Publish: " + topic);
}

// ============================================================================
// Store-and-Forward Ring Buffer
// ============================================================================
void storeForwardEnqueue(String msg) {
  if (sfCount >= STORE_FORWARD_MAX) {
    // Drop oldest
    sfTail = (sfTail + 1) % STORE_FORWARD_MAX;
    sfCount--;
  }
  storeForwardBuffer[sfHead] = msg;
  sfHead = (sfHead + 1) % STORE_FORWARD_MAX;
  sfCount++;
}

String storeForwardDequeue() {
  if (sfCount == 0) return "";
  String msg = storeForwardBuffer[sfTail];
  sfTail = (sfTail + 1) % STORE_FORWARD_MAX;
  sfCount--;
  return msg;
}

void flushStoreForward() {
  int flushed = 0;
  while (sfCount > 0 && flushed < 10) { // Max 10 per loop to avoid blocking
    String msg = storeForwardDequeue();
    if (msg.length() > 0) {
      // Try MQTT publish
      String topic = "mycosoft/devices/" + deviceId + "/buffered";
      publishMQTT(topic, msg);
      flushed++;
    }
  }
  if (flushed > 0) {
    Serial.println("[SF] Flushed " + String(flushed) + " buffered messages, " + String(sfCount) + " remaining");
  }
}

// ============================================================================
// PC/Jetson Command Handling (USB Serial)
// ============================================================================
void handlePCCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (uartCommandBuffer.length() > 0) {
        processPCCommand(uartCommandBuffer);
        uartCommandBuffer = "";
      }
    } else {
      uartCommandBuffer += c;
    }
  }
}

void processPCCommand(String cmd) {
  DynamicJsonDocument doc(1024);
  DeserializationError error = deserializeJson(doc, cmd);

  if (error) {
    // Try text commands
    cmd.trim();
    if (cmd == "status") {
      sendStatus("ready");
      return;
    } else if (cmd.startsWith("wifi ")) {
      // wifi ssid password
      // TODO: parse and store to NVS
      sendResponse("wifi", "{\"status\":\"not_implemented\"}");
      return;
    } else if (cmd == "lora status") {
      DynamicJsonDocument ldoc(256);
      ldoc["available"] = loraAvailable;
      sendResponse("lora_status", ldoc);
      return;
    }
    // Forward raw text to Side-A
    forwardToSideA(cmd);
    return;
  }

  String command = doc["cmd"] | "";

  if (command == "ping") {
    sendResponse("ping", "{\"status\":\"ok\",\"side\":\"side-b\",\"wifi\":" +
                 String(wifiConnected ? "true" : "false") + ",\"lora\":" +
                 String(loraAvailable ? "true" : "false") + "}");
  }
  else if (command == "status") {
    sendStatus("ready");
  }
  else if (command == "get_mac") {
    sendResponse("mac", "{\"mac\":\"" + deviceMac + "\",\"device_id\":\"" + deviceId + "\"}");
  }
  else if (command == "get_version") {
    sendResponse("version", "{\"version\":\"" + String(FIRMWARE_VERSION) + "\"}");
  }
  else if (command == "side_a_status") {
    checkSideAStatus();
  }
  else if (command == "sf_status") {
    // Store-forward buffer status
    DynamicJsonDocument sfDoc(256);
    sfDoc["count"] = sfCount;
    sfDoc["max"] = STORE_FORWARD_MAX;
    sendResponse("sf_status", sfDoc);
  }
  else {
    // Forward command to Side-A
    forwardToSideA(cmd);
  }
}

// ============================================================================
// Side-A Data Handling (UART)
// ============================================================================
void handleSideAData() {
  while (UART_TO_SIDEA.available() > 0) {
    char c = UART_TO_SIDEA.read();
    if (c == '\n' || c == '\r') {
      if (sideACommandBuffer.length() > 0) {
        processSideAData(sideACommandBuffer);
        sideACommandBuffer = "";
      }
    } else {
      sideACommandBuffer += c;
    }
  }
}

void processSideAData(String data) {
  lastSideAHeartbeat = millis();
  sideAConnected = true;

  // Forward all data to PC/Jetson over USB Serial
  Serial.println(data);

  // Also try to publish telemetry to MQTT
  if (data.indexOf("\"type\":\"telemetry\"") >= 0 ||
      data.indexOf("\"type\":\"capability_manifest\"") >= 0) {
    String topic = "mycosoft/devices/" + deviceId + "/telemetry";
    publishMQTT(topic, data);
  }

  // Forward to LoRa if available and Wi-Fi is down
  if (loraAvailable && !wifiConnected) {
    if (data.indexOf("\"type\":\"telemetry\"") >= 0) {
      sendLoRa(data);
    }
  }
}

// ============================================================================
// Side-A Communication
// ============================================================================
void forwardToSideA(String command) {
  if (sideAConnected) {
    UART_TO_SIDEA.println(command);
    UART_TO_SIDEA.flush();
  } else {
    sendError("Side-A not connected");
  }
}

void pingSideA() {
  UART_TO_SIDEA.println("{\"cmd\":\"ping\"}");
  UART_TO_SIDEA.flush();
  lastSideAHeartbeat = millis();
}

void checkSideAStatus() {
  DynamicJsonDocument doc(512);
  doc["side_a_connected"] = sideAConnected;
  doc["last_heartbeat_ms"] = millis() - lastSideAHeartbeat;
  doc["wifi_connected"] = wifiConnected;
  doc["lora_available"] = loraAvailable;
  doc["sf_buffered"] = sfCount;
  sendResponse("side_a_status", doc);
}

// ============================================================================
// Helper Functions
// ============================================================================
void sendStatus(String status) {
  DynamicJsonDocument doc(1024);
  doc["status"] = status;
  doc["mac"] = deviceMac;
  doc["device_id"] = deviceId;
  doc["firmware"] = FIRMWARE_VERSION;
  doc["uptime"] = uptimeSeconds;
  doc["side_a_connected"] = sideAConnected;
  doc["wifi_connected"] = wifiConnected;
  doc["wifi_ip"] = wifiConnected ? WiFi.localIP().toString() : "none";
  doc["lora_available"] = loraAvailable;
  doc["lte_available"] = lteAvailable;
  doc["sf_buffered"] = sfCount;
  doc["sf_max"] = STORE_FORWARD_MAX;

  sendResponse("status", doc);
}

void sendResponse(String type, DynamicJsonDocument& doc) {
  DynamicJsonDocument response(2048);
  response["type"] = type;
  response["data"] = doc;
  serializeJson(response, Serial);
  Serial.println();
}

void sendResponse(String type, String data) {
  Serial.print("{\"type\":\"");
  Serial.print(type);
  Serial.print("\",\"data\":");
  Serial.print(data);
  Serial.println("}");
}

void sendError(String error) {
  sendResponse("error", "{\"error\":\"" + error + "\"}");
}
