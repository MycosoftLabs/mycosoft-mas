/*
 * MycoBrain Side-A — Minimal API Firmware (no sensors)
 *
 * Goal:
 * - Boot reliably (even when sensors are unplugged)
 * - Speak simple newline-delimited JSON over Serial for the website/MycoBrain service
 *
 * Compatible with:
 * - services/mycobrain/mycobrain_dual_service.py (JSON fallback mode)
 *
 * Commands (JSON, newline terminated):
 * - {"cmd":"ping"}
 * - {"cmd":"get_mac"}
 * - {"cmd":"get_version"}
 * - {"cmd":"status"}
 * - {"cmd":"i2c_scan"}
 * - {"cmd":"set_telemetry_interval","ms":5000}
 *
 * Also supports workbook-style command envelopes:
 * - {"type":"cmd","id":"c-001","op":"status"}
 * - {"type":"cmd","id":"c-002","op":"i2c.scan"}
 * - {"type":"cmd","id":"c-003","op":"telemetry.period","period_ms":1000}
 */

#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include "soc/rtc_cntl_reg.h"

// MycoBrain Side-A pins (from prior working notes)
static const uint8_t SDA_PIN = 5;
static const uint8_t SCL_PIN = 4;

static const uint32_t SERIAL_BAUD = 115200;
static const uint32_t TELEMETRY_DEFAULT_MS = 5000;
static const char* FW_VERSION = "sidea-min-api-0.2";

static uint32_t telemetryIntervalMs = TELEMETRY_DEFAULT_MS;
static uint32_t lastTelemetryMs = 0;
static uint8_t lastI2cAddrs[32];
static uint8_t lastI2cCount = 0;

static String nodeIdFromEfuse() {
  const uint64_t efuse = ESP.getEfuseMac();
  const uint8_t mac0 = (efuse >> 40) & 0xFF;
  const uint8_t mac1 = (efuse >> 32) & 0xFF;
  const uint8_t mac2 = (efuse >> 24) & 0xFF;
  const uint8_t mac3 = (efuse >> 16) & 0xFF;
  const uint8_t mac4 = (efuse >> 8) & 0xFF;
  const uint8_t mac5 = (efuse >> 0) & 0xFF;

  char buf[24];
  snprintf(buf, sizeof(buf), "A-%02X:%02X:%02X:%02X:%02X:%02X",
    mac0, mac1, mac2, mac3, mac4, mac5);
  return String(buf);
}

static String readLineFromSerial() {
  static String line;
  while (Serial.available() > 0) {
    const char c = (char)Serial.read();
    if (c == '\n') {
      String out = line;
      line = "";
      out.trim();
      return out;
    }
    if (c != '\r')
      line += c;
  }
  return "";
}

static void writeJson(const JsonDocument& doc) {
  serializeJson(doc, Serial);
  Serial.write('\n');
  Serial.flush();
}

static void writeError(const char* message) {
  StaticJsonDocument<256> doc;
  doc["ok"] = false;
  doc["error"] = message;
  writeJson(doc);
}

static void sendAckIfNeeded(const JsonDocument& req, bool ok, const char* err = nullptr) {
  const char* type = req["type"] | "";
  const char* id = req["id"] | "";
  if (strcmp(type, "cmd") != 0 || id[0] == '\0')
    return;

  StaticJsonDocument<256> doc;
  doc["type"] = "ack";
  doc["id"] = id;
  doc["ok"] = ok;
  if (!ok && err)
    doc["err"] = err;
  writeJson(doc);
}

static void i2cScanNow() {
  lastI2cCount = 0;
  for (uint8_t addr = 0x08; addr < 0x78; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      if (lastI2cCount < sizeof(lastI2cAddrs))
        lastI2cAddrs[lastI2cCount++] = addr;
    }
    yield();
  }
}

static void handleCmd(const JsonDocument& req) {
  const char* cmd = req["cmd"] | "";
  const char* type = req["type"] | "";
  const char* op = req["op"] | "";

  // Back-compat: allow workbook-style type/op to map to cmd
  if (cmd[0] == '\0' && strcmp(type, "cmd") == 0 && op[0] != '\0')
    cmd = op;

  if (cmd[0] == '\0') {
    writeError("missing cmd");
    sendAckIfNeeded(req, false, "missing_cmd");
    return;
  }

  if (strcmp(cmd, "ping") == 0) {
    StaticJsonDocument<128> doc;
    doc["ok"] = true;
    doc["pong"] = true;
    writeJson(doc);
    sendAckIfNeeded(req, true);
    return;
  }

  if (strcmp(cmd, "get_mac") == 0 || strcmp(cmd, "identity") == 0) {
    const String nodeId = nodeIdFromEfuse();
    const String macStr = nodeId.substring(2); // strip "A-"

    StaticJsonDocument<256> doc;
    doc["ok"] = true;
    doc["mac"] = macStr;
    doc["node_id"] = nodeId;
    doc["role"] = "side-a";
    writeJson(doc);
    sendAckIfNeeded(req, true);
    return;
  }

  if (strcmp(cmd, "get_version") == 0) {
    StaticJsonDocument<256> doc;
    doc["ok"] = true;
    doc["version"] = FW_VERSION;
    doc["build"] = __DATE__ " " __TIME__;
    writeJson(doc);
    sendAckIfNeeded(req, true);
    return;
  }

  if (strcmp(cmd, "status") == 0 || strcmp(cmd, "status.get") == 0) {
    StaticJsonDocument<256> doc;
    doc["ok"] = true;
    doc["uptime_ms"] = millis();
    doc["uptime_seconds"] = millis() / 1000;
    doc["firmware_version"] = FW_VERSION;
    doc["telemetry_interval_ms"] = telemetryIntervalMs;
    writeJson(doc);
    sendAckIfNeeded(req, true);
    return;
  }

  if (strcmp(cmd, "set_telemetry_interval") == 0 || strcmp(cmd, "telemetry.period") == 0) {
    const uint32_t ms = req["ms"] | (req["period_ms"] | telemetryIntervalMs);
    telemetryIntervalMs = (ms < 250) ? 250 : ms;
    StaticJsonDocument<192> doc;
    doc["ok"] = true;
    doc["telemetry_interval_ms"] = telemetryIntervalMs;
    writeJson(doc);
    sendAckIfNeeded(req, true);
    return;
  }

  if (strcmp(cmd, "i2c_scan") == 0 || strcmp(cmd, "i2c.scan") == 0) {
    i2cScanNow();
    StaticJsonDocument<512> doc;
    doc["ok"] = true;
    JsonArray addrs = doc.createNestedArray("i2c");
    for (uint8_t i = 0; i < lastI2cCount; i++)
      addrs.add(lastI2cAddrs[i]);
    writeJson(doc);
    sendAckIfNeeded(req, true);
    return;
  }

  writeError("unknown cmd");
  sendAckIfNeeded(req, false, "unknown_cmd");
}

static void sendTelemetry() {
  // Match the website expectations in components/mycobrain-device-manager.tsx:
  // telemetry.temperature/humidity/pressure/gas_resistance/ai*_voltage/mosfet_states/i2c_addresses/firmware_version/uptime_seconds
  StaticJsonDocument<512> doc;
  doc["t_ms"] = millis();
  doc["seq"] = (uint32_t)(millis() / (telemetryIntervalMs ? telemetryIntervalMs : 1));
  doc["node"] = nodeIdFromEfuse();
  doc["uptime_seconds"] = millis() / 1000;
  doc["firmware_version"] = FW_VERSION;
  doc["temperature"] = nullptr;
  doc["humidity"] = nullptr;
  doc["pressure"] = nullptr;
  doc["gas_resistance"] = nullptr;

  JsonArray i2c = doc.createNestedArray("i2c_addresses");
  for (uint8_t i = 0; i < lastI2cCount; i++)
    i2c.add(lastI2cAddrs[i]);

  // Placeholders for MycoBrain UI fields
  doc["ai1_voltage"] = nullptr;
  doc["ai2_voltage"] = nullptr;
  doc["ai3_voltage"] = nullptr;
  doc["ai4_voltage"] = nullptr;
  JsonArray mosfets = doc.createNestedArray("mosfet_states");
  mosfets.add(false);
  mosfets.add(false);
  mosfets.add(false);
  mosfets.add(false);
  doc["note"] = "sensors_unplugged";
  writeJson(doc);
}

void setup() {
  // If the chip is browning out before setup, that’s hardware; but still disable ASAP.
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  // Reduce CPU a bit to reduce peak draw.
  setCpuFrequencyMhz(80);

  Serial.begin(SERIAL_BAUD);
  delay(250);

  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000);

  StaticJsonDocument<256> hello;
  hello["ok"] = true;
  hello["hello"] = "mycobrain-sidea-min-api";
  hello["version"] = FW_VERSION;
  hello["node_id"] = nodeIdFromEfuse();
  hello["role"] = "side-a";
  hello["baud"] = SERIAL_BAUD;
  writeJson(hello);

  // Prime an initial I2C scan so the UI has something to show.
  i2cScanNow();
}

void loop() {
  yield();

  const String line = readLineFromSerial();
  if (line.length() > 0) {
    StaticJsonDocument<512> req;
    const DeserializationError err = deserializeJson(req, line);
    if (err) {
      writeError("bad json");
    } else {
      handleCmd(req);
    }
  }

  const uint32_t now = millis();
  if (now - lastTelemetryMs >= telemetryIntervalMs) {
    sendTelemetry();
    lastTelemetryMs = now;
  }
}



