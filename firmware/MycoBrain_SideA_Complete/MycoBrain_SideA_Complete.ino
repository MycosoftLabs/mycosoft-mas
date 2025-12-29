/*
 * MycoBrain Side-A Complete Firmware
 * Based on Garrett's ESP32AB workbook + working BSEC2 code
 *
 * Board: ESP32-S3 (16MB Flash, OPI PSRAM)
 * Arduino IDE Settings:
 *   - USB CDC on boot: Enabled
 *   - USB DFU on boot: Enabled (requires USB OTG mode)
 *   - USB firmware MSC on boot: Disabled
 *   - USB Mode: Hardware CDC and JTAG
 *   - JTAG Adapter: Integrated USB JTAG
 *   - PSRAM: OPI PSRAM
 *   - CPU Frequency: 240 MHz
 *   - Flash Mode: QIO @ 80 MHz
 *   - Flash Size: 16 MB
 *   - Partition Scheme: 16MB Flash, 3MB App / 9.9MB FATFS
 *   - Upload Speed: 921600
 *   - Events Run On: Core 1
 *   - Arduino Runs On: Core 1
 *
 * Hardware Notes:
 *   - Bridged board (diode removed, wire bridge) - requires brownout disable
 *   - SDA=5, SCL=4 (per ESP32AB workbook)
 *   - AO_PINS[0-2] = {12,13,14} for RGB PWM indicators
 *   - BUZZER_PIN = 16
 *
 * Protocol:
 *   - JSONL over USB CDC (115200 baud)
 *   - Supports simple {"cmd":"..."} commands (MycoBrain service)
 *   - Supports workbook {"type":"cmd","id":"...","op":"..."} commands
 *   - Emits {"type":"tele",...} telemetry frames (workbook style)
 *   - Also emits website-compatible flat telemetry for MycoBrain UI
 */

#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>

// Brownout disable for bridged board
#include "soc/rtc_cntl_reg.h"

// ============================================================
// PIN CONFIGURATION (ESP32AB Workbook defaults)
// ============================================================
static const uint8_t PIN_SDA = 5;
static const uint8_t PIN_SCL = 4;
static const uint32_t I2C_FREQ = 100000;

// Analog input pins (for future sensors)
static const uint8_t AIN_PINS[4] = {6, 7, 10, 11};

// Analog output / PWM indicator LED pins (RGB)
static const uint8_t AO_PINS[3] = {12, 13, 14};  // R, G, B

// Buzzer
static const uint8_t BUZZER_PIN = 16;

// ============================================================
// FIRMWARE INFO
// ============================================================
static const char* FW_NAME = "mycobrain.sideA";
static const char* FW_VERSION = "1.0.0";
static const uint32_t SCHEMA_VER = 3;

// ============================================================
// TIMING CONFIGURATION
// ============================================================
static const uint32_t SERIAL_BAUD = 115200;
static const uint32_t BOOT_WAIT_MS = 1500;  // Time for USB CDC to attach
static uint32_t telemetryIntervalMs = 2000;
static uint32_t lastTelemetryMs = 0;
static uint32_t bootMs = 0;
static uint32_t seq = 0;

// ============================================================
// I2C SCAN CACHE
// ============================================================
static uint8_t i2cAddrs[32];
static uint8_t i2cCount = 0;

// ============================================================
// LED STATE MACHINE
// ============================================================
enum LedMode : uint8_t {
  LED_OFF = 0,
  LED_STATE = 1,
  LED_MANUAL = 2
};
static LedMode ledMode = LED_STATE;
static uint8_t ledR = 0, ledG = 0, ledB = 0;

enum DeviceState : uint8_t {
  STATE_BOOT = 0,
  STATE_INIT = 1,
  STATE_OK = 2,
  STATE_WARN = 3,
  STATE_ERROR = 4
};
static DeviceState deviceState = STATE_BOOT;

// ============================================================
// SENSOR READINGS (placeholders when sensors unplugged)
// ============================================================
struct SensorData {
  bool valid = false;
  float temperature = NAN;
  float humidity = NAN;
  float pressure = NAN;
  float gasResistance = NAN;
  float iaq = NAN;
  float co2eq = NAN;
  float vocIdx = NAN;
};
static SensorData sensorData;

// ============================================================
// LED FUNCTIONS
// ============================================================
static void ledWriteRGB(uint8_t r, uint8_t g, uint8_t b) {
  analogWrite(AO_PINS[0], r);
  analogWrite(AO_PINS[1], g);
  analogWrite(AO_PINS[2], b);
}

static void ledOff() {
  ledWriteRGB(0, 0, 0);
}

static void ledBootBlink() {
  for (int i = 0; i < 3; i++) {
    ledWriteRGB(0, 0, 60);
    delay(60);
    ledWriteRGB(0, 60, 0);
    delay(60);
    ledWriteRGB(60, 0, 0);
    delay(60);
    ledOff();
    delay(40);
  }
}

static void ledUpdate() {
  if (ledMode == LED_OFF) {
    ledOff();
    return;
  }
  if (ledMode == LED_MANUAL) {
    ledWriteRGB(ledR, ledG, ledB);
    return;
  }

  // State machine LED patterns
  const uint32_t t = millis();
  switch (deviceState) {
    case STATE_BOOT:
      // Blue pulse
      {
        uint8_t v = (uint8_t)(30 + 30 * sin((double)t / 300.0));
        ledWriteRGB(0, 0, v);
      }
      break;

    case STATE_INIT:
      // Blue breathing
      {
        uint8_t v = (uint8_t)(20 + 40 * sin((double)t / 500.0));
        ledWriteRGB(0, 0, v);
      }
      break;

    case STATE_OK:
      // Gentle green pulse
      {
        uint8_t v = (uint8_t)(40 + 20 * sin((double)t / 800.0));
        ledWriteRGB(0, v, 0);
      }
      break;

    case STATE_WARN:
      // Yellow
      ledWriteRGB(60, 40, 0);
      break;

    case STATE_ERROR:
      // Red blink
      {
        bool on = ((t / 250) % 2) == 0;
        ledWriteRGB(on ? 80 : 0, 0, 0);
      }
      break;
  }
}

// ============================================================
// BUZZER FUNCTIONS
// ============================================================
static void beep(int freqHz = 2000, int ms = 50) {
  tone(BUZZER_PIN, freqHz, ms);
}

static void bootChime() {
  tone(BUZZER_PIN, 523, 60);  // C5
  delay(70);
  tone(BUZZER_PIN, 659, 60);  // E5
  delay(70);
  tone(BUZZER_PIN, 784, 80);  // G5
  delay(90);
  noTone(BUZZER_PIN);
}

// ============================================================
// UTILITY: MAC / NODE ID
// ============================================================
static String getNodeId() {
  const uint64_t efuse = ESP.getEfuseMac();
  char buf[24];
  snprintf(buf, sizeof(buf), "A-%02X:%02X:%02X:%02X:%02X:%02X",
    (uint8_t)(efuse >> 40), (uint8_t)(efuse >> 32),
    (uint8_t)(efuse >> 24), (uint8_t)(efuse >> 16),
    (uint8_t)(efuse >> 8), (uint8_t)(efuse));
  return String(buf);
}

static String getMac() {
  const uint64_t efuse = ESP.getEfuseMac();
  char buf[18];
  snprintf(buf, sizeof(buf), "%02X:%02X:%02X:%02X:%02X:%02X",
    (uint8_t)(efuse >> 40), (uint8_t)(efuse >> 32),
    (uint8_t)(efuse >> 24), (uint8_t)(efuse >> 16),
    (uint8_t)(efuse >> 8), (uint8_t)(efuse));
  return String(buf);
}

// ============================================================
// JSON HELPERS
// ============================================================
static void writeJson(const JsonDocument& doc) {
  serializeJson(doc, Serial);
  Serial.write('\n');
  Serial.flush();
}

static void writeError(const char* msg) {
  StaticJsonDocument<256> doc;
  doc["ok"] = false;
  doc["error"] = msg;
  writeJson(doc);
}

static void sendAck(const char* id, bool ok, const char* err = nullptr) {
  StaticJsonDocument<256> doc;
  doc["type"] = "ack";
  doc["id"] = id;
  doc["ok"] = ok;
  if (!ok && err)
    doc["err"] = err;
  writeJson(doc);
}

// ============================================================
// I2C SCAN
// ============================================================
static void i2cScan() {
  i2cCount = 0;
  for (uint8_t addr = 0x08; addr < 0x78; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      if (i2cCount < sizeof(i2cAddrs))
        i2cAddrs[i2cCount++] = addr;
    }
    yield();
  }
}

// ============================================================
// COMMAND HANDLER
// ============================================================
static void handleCommand(const JsonDocument& req) {
  // Extract command from either format
  const char* cmd = req["cmd"] | "";
  const char* type = req["type"] | "";
  const char* op = req["op"] | "";
  const char* id = req["id"] | "";

  // Workbook format: {"type":"cmd","op":"..."} -> use op as cmd
  if (cmd[0] == '\0' && strcmp(type, "cmd") == 0 && op[0] != '\0')
    cmd = op;

  if (cmd[0] == '\0') {
    writeError("missing_cmd");
    if (id[0] != '\0') sendAck(id, false, "missing_cmd");
    return;
  }

  // ---- PING ----
  if (strcmp(cmd, "ping") == 0) {
    StaticJsonDocument<128> doc;
    doc["ok"] = true;
    doc["pong"] = true;
    writeJson(doc);
    if (id[0] != '\0') sendAck(id, true);
    return;
  }

  // ---- GET_MAC / IDENTITY ----
  if (strcmp(cmd, "get_mac") == 0 || strcmp(cmd, "identity") == 0) {
    StaticJsonDocument<256> doc;
    doc["ok"] = true;
    doc["mac"] = getMac();
    doc["node_id"] = getNodeId();
    doc["role"] = "side-a";
    doc["firmware"] = FW_VERSION;
    writeJson(doc);
    if (id[0] != '\0') sendAck(id, true);
    return;
  }

  // ---- GET_VERSION ----
  if (strcmp(cmd, "get_version") == 0 || strcmp(cmd, "version") == 0) {
    StaticJsonDocument<256> doc;
    doc["ok"] = true;
    doc["version"] = FW_VERSION;
    doc["firmware"] = FW_NAME;
    doc["schema_ver"] = SCHEMA_VER;
    doc["build"] = __DATE__ " " __TIME__;
    doc["chip"] = ESP.getChipModel();
    doc["cpu_mhz"] = ESP.getCpuFreqMHz();
    writeJson(doc);
    if (id[0] != '\0') sendAck(id, true);
    return;
  }

  // ---- STATUS ----
  if (strcmp(cmd, "status") == 0 || strcmp(cmd, "status.get") == 0) {
    StaticJsonDocument<512> doc;
    doc["ok"] = true;
    doc["node_id"] = getNodeId();
    doc["uptime_ms"] = millis() - bootMs;
    doc["uptime_s"] = (millis() - bootMs) / 1000;
    doc["heap"] = ESP.getFreeHeap();
    doc["firmware_version"] = FW_VERSION;
    doc["telemetry_period_ms"] = telemetryIntervalMs;
    doc["i2c_count"] = i2cCount;
    doc["state"] = (uint8_t)deviceState;
    writeJson(doc);
    if (id[0] != '\0') sendAck(id, true);
    return;
  }

  // ---- I2C_SCAN ----
  if (strcmp(cmd, "i2c_scan") == 0 || strcmp(cmd, "i2c.scan") == 0) {
    i2cScan();
    StaticJsonDocument<512> doc;
    doc["ok"] = true;
    doc["count"] = i2cCount;
    JsonArray arr = doc.createNestedArray("i2c");
    for (uint8_t i = 0; i < i2cCount; i++) {
      char hex[8];
      snprintf(hex, sizeof(hex), "0x%02X", i2cAddrs[i]);
      arr.add(hex);
    }
    writeJson(doc);
    if (id[0] != '\0') sendAck(id, true);
    return;
  }

  // ---- SET TELEMETRY INTERVAL ----
  if (strcmp(cmd, "set_telemetry_interval") == 0 ||
      strcmp(cmd, "telemetry.period") == 0 ||
      strcmp(cmd, "telemetry.set") == 0) {
    uint32_t ms = req["ms"] | (req["period_ms"] | telemetryIntervalMs);
    telemetryIntervalMs = (ms < 200) ? 200 : (ms > 60000 ? 60000 : ms);
    StaticJsonDocument<192> doc;
    doc["ok"] = true;
    doc["telemetry_interval_ms"] = telemetryIntervalMs;
    writeJson(doc);
    if (id[0] != '\0') sendAck(id, true);
    return;
  }

  // ---- CONFIG GET ----
  if (strcmp(cmd, "config") == 0 || strcmp(cmd, "config.get") == 0) {
    StaticJsonDocument<768> doc;
    doc["ok"] = true;
    auto schema = doc.createNestedObject("schema");
    schema["name"] = FW_NAME;
    schema["ver"] = SCHEMA_VER;
    auto device = doc.createNestedObject("device");
    device["node_id"] = getNodeId();
    device["role"] = "side-a";
    auto pins = doc.createNestedObject("pins");
    auto i2c = pins.createNestedObject("i2c");
    i2c["sda"] = PIN_SDA;
    i2c["scl"] = PIN_SCL;
    i2c["freq_hz"] = I2C_FREQ;
    auto timing = doc.createNestedObject("timing");
    timing["telemetry_period_ms"] = telemetryIntervalMs;
    writeJson(doc);
    if (id[0] != '\0') sendAck(id, true);
    return;
  }

  // ---- LED CONTROL ----
  if (strcmp(cmd, "led") == 0 || strcmp(cmd, "led.set") == 0) {
    const char* mode = req["mode"] | "";
    if (strcmp(mode, "off") == 0) {
      ledMode = LED_OFF;
    } else if (strcmp(mode, "state") == 0) {
      ledMode = LED_STATE;
    } else if (strcmp(mode, "manual") == 0) {
      ledMode = LED_MANUAL;
      ledR = req["r"] | 0;
      ledG = req["g"] | 0;
      ledB = req["b"] | 0;
    } else if (req.containsKey("r") || req.containsKey("g") || req.containsKey("b")) {
      ledMode = LED_MANUAL;
      ledR = req["r"] | ledR;
      ledG = req["g"] | ledG;
      ledB = req["b"] | ledB;
    }
    StaticJsonDocument<192> doc;
    doc["ok"] = true;
    doc["led_mode"] = ledMode == LED_OFF ? "off" : (ledMode == LED_STATE ? "state" : "manual");
    doc["r"] = ledR;
    doc["g"] = ledG;
    doc["b"] = ledB;
    writeJson(doc);
    if (id[0] != '\0') sendAck(id, true);
    return;
  }

  // ---- BEEP ----
  if (strcmp(cmd, "beep") == 0) {
    int freq = req["freq"] | 2000;
    int ms = req["ms"] | 100;
    beep(freq, ms);
    StaticJsonDocument<128> doc;
    doc["ok"] = true;
    writeJson(doc);
    if (id[0] != '\0') sendAck(id, true);
    return;
  }

  // ---- REBOOT ----
  if (strcmp(cmd, "reboot") == 0 || strcmp(cmd, "restart") == 0) {
    StaticJsonDocument<128> doc;
    doc["ok"] = true;
    doc["rebooting"] = true;
    writeJson(doc);
    if (id[0] != '\0') sendAck(id, true);
    delay(100);
    ESP.restart();
    return;
  }

  // ---- HELP ----
  if (strcmp(cmd, "help") == 0) {
    StaticJsonDocument<512> doc;
    doc["ok"] = true;
    JsonArray cmds = doc.createNestedArray("commands");
    cmds.add("ping");
    cmds.add("get_mac");
    cmds.add("get_version");
    cmds.add("status");
    cmds.add("i2c_scan");
    cmds.add("config");
    cmds.add("set_telemetry_interval");
    cmds.add("led");
    cmds.add("beep");
    cmds.add("reboot");
    cmds.add("help");
    writeJson(doc);
    if (id[0] != '\0') sendAck(id, true);
    return;
  }

  // Unknown command
  writeError("unknown_cmd");
  if (id[0] != '\0') sendAck(id, false, "unknown_cmd");
}

// ============================================================
// TELEMETRY OUTPUT
// ============================================================
static void sendTelemetry() {
  const uint32_t t = millis() - bootMs;
  const uint32_t uptimeSec = t / 1000;

  // Workbook-style telemetry frame
  StaticJsonDocument<768> doc;
  doc["type"] = "tele";
  doc["seq"] = seq++;
  doc["t_ms"] = t;
  doc["node"] = getNodeId();
  doc["uptime_s"] = uptimeSec;
  doc["uptime_seconds"] = uptimeSec;  // Website compatibility

  // Environment data
  auto env = doc.createNestedObject("env");
  if (sensorData.valid) {
    env["temp_c"] = sensorData.temperature;
    env["rh_pct"] = sensorData.humidity;
    env["press_hpa"] = sensorData.pressure;
    env["gas_ohm"] = sensorData.gasResistance;
    env["iaq"] = sensorData.iaq;
    env["co2eq"] = sensorData.co2eq;
    env["voc_idx"] = sensorData.vocIdx;
  } else {
    // Sensors unplugged - null values
    env["temp_c"] = nullptr;
    env["rh_pct"] = nullptr;
    env["press_hpa"] = nullptr;
  }

  // Website-compatible flat fields
  if (sensorData.valid) {
    doc["temperature"] = sensorData.temperature;
    doc["humidity"] = sensorData.humidity;
    doc["pressure"] = sensorData.pressure;
    doc["gas_resistance"] = sensorData.gasResistance;
  } else {
    doc["temperature"] = nullptr;
    doc["humidity"] = nullptr;
    doc["pressure"] = nullptr;
    doc["gas_resistance"] = nullptr;
  }
  doc["firmware_version"] = FW_VERSION;

  // I2C addresses
  JsonArray i2cArr = doc.createNestedArray("i2c_addresses");
  for (uint8_t i = 0; i < i2cCount; i++)
    i2cArr.add(i2cAddrs[i]);

  // Health info
  auto health = doc.createNestedObject("health");
  health["heap"] = ESP.getFreeHeap();
  health["i2c_ok"] = (i2cCount > 0);
  health["state"] = (uint8_t)deviceState;

  // Analog inputs (placeholders)
  doc["ai1_voltage"] = nullptr;
  doc["ai2_voltage"] = nullptr;
  doc["ai3_voltage"] = nullptr;
  doc["ai4_voltage"] = nullptr;

  // MOSFET states (placeholders)
  JsonArray mosfets = doc.createNestedArray("mosfet_states");
  mosfets.add(false);
  mosfets.add(false);
  mosfets.add(false);
  mosfets.add(false);

  writeJson(doc);
}

// ============================================================
// SERIAL INPUT HANDLER
// ============================================================
static String serialBuffer;

static void processSerialInput() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n') {
      serialBuffer.trim();
      if (serialBuffer.length() > 0) {
        StaticJsonDocument<512> req;
        DeserializationError err = deserializeJson(req, serialBuffer);
        if (err) {
          writeError("bad_json");
        } else {
          handleCommand(req);
        }
      }
      serialBuffer = "";
    } else if (c != '\r') {
      serialBuffer += c;
      // Prevent buffer overflow
      if (serialBuffer.length() > 2048)
        serialBuffer = "";
    }
  }
}

// ============================================================
// SETUP
// ============================================================
void setup() {
  // CRITICAL: Disable brownout detector FIRST for bridged board
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  // Note: Using 240 MHz as per user's known working settings
  // (Don't lower CPU; the board needs the settings that worked)

  // Initialize serial
  Serial.begin(SERIAL_BAUD);

  // Wait for USB CDC to attach (ESP32-S3 quirk)
  delay(BOOT_WAIT_MS);

  bootMs = millis();

  // Initialize I2C
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(I2C_FREQ);

  // Initialize LED pins for PWM
  for (int i = 0; i < 3; i++) {
    pinMode(AO_PINS[i], OUTPUT);
  }
  pinMode(BUZZER_PIN, OUTPUT);

  // Boot sequence
  deviceState = STATE_BOOT;
  ledBootBlink();
  bootChime();

  // Initial I2C scan
  deviceState = STATE_INIT;
  i2cScan();

  // Determine initial state
  if (i2cCount > 0) {
    deviceState = STATE_OK;
  } else {
    deviceState = STATE_WARN;  // No sensors found, but we're running
  }

  // Send boot message
  StaticJsonDocument<384> hello;
  hello["ok"] = true;
  hello["type"] = "boot";
  hello["hello"] = FW_NAME;
  hello["version"] = FW_VERSION;
  hello["node_id"] = getNodeId();
  hello["mac"] = getMac();
  hello["role"] = "side-a";
  hello["baud"] = SERIAL_BAUD;
  hello["i2c_count"] = i2cCount;
  hello["chip"] = ESP.getChipModel();
  hello["cpu_mhz"] = ESP.getCpuFreqMHz();
  hello["heap"] = ESP.getFreeHeap();
  writeJson(hello);
}

// ============================================================
// LOOP
// ============================================================
void loop() {
  yield();

  // Process incoming commands
  processSerialInput();

  // Update LED state machine
  ledUpdate();

  // Periodic telemetry
  const uint32_t now = millis();
  if (now - lastTelemetryMs >= telemetryIntervalMs) {
    lastTelemetryMs = now;
    sendTelemetry();
  }
}

