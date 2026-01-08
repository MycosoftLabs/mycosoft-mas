/*
 * MycoBrain Side-A — Dual Mode Firmware (CLI + JSON)
 * 
 * This firmware accepts BOTH:
 *   - CLI commands: "status", "help", "scan", etc. (for Arduino Serial Monitor debugging)
 *   - JSON commands: {"cmd":"status"}, {"type":"cmd","op":"status"}, etc. (for website/service)
 * 
 * Output modes:
 *   - Default: JSON (for website compatibility)
 *   - Can switch to CLI output with "fmt lines" command
 *   - Can switch to JSON output with "fmt json" command
 * 
 * Based on Garrett's ESP32AB workbook + working BSEC2 code structure.
 * 
 * Arduino IDE Settings (known working for MycoBrain bridged board):
 *   - USB CDC on boot: Enabled
 *   - USB Mode: Hardware CDC and JTAG
 *   - PSRAM: OPI PSRAM
 *   - CPU Frequency: 240 MHz
 *   - Flash Mode: QIO @ 80 MHz
 *   - Flash Size: 16 MB
 *   - Partition Scheme: 16MB Flash, 3MB App / 9.9MB FATFS
 *   - Upload Speed: 921600
 */

#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>

// Brownout disable for bridged board
#include "soc/rtc_cntl_reg.h"

// ============================================================
// PIN CONFIGURATION (ESP32AB Workbook)
// ============================================================
static const uint8_t PIN_SDA = 5;
static const uint8_t PIN_SCL = 4;
static const uint32_t I2C_FREQ = 100000;

// RGB LED PWM pins (from Garrett's code)
static const uint8_t AO_PINS[3] = {12, 13, 14};  // MOSFET outputs (not LEDs!)

// NeoPixel on GPIO15 (SK6805)
#define NEOPIXEL_PIN 15
#define PIXEL_COUNT 1
Adafruit_NeoPixel pixels(PIXEL_COUNT, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);

// Buzzer
static const uint8_t BUZZER_PIN = 16;

// ============================================================
// FIRMWARE INFO
// ============================================================
static const char* FW_NAME = "mycobrain.sideA.dualmode";
static const char* FW_VERSION = "1.1.0";
static const uint32_t SCHEMA_VER = 3;

// ============================================================
// OUTPUT FORMAT MODE
// ============================================================
enum OutputFormat { FMT_JSON = 0, FMT_LINES = 1 };
static OutputFormat gOutputFormat = FMT_JSON;

// ============================================================
// TIMING
// ============================================================
static const uint32_t SERIAL_BAUD = 115200;
static const uint32_t BOOT_WAIT_MS = 1800;  // Match Garrett's boot wait
static uint32_t telemetryIntervalMs = 2000;
static uint32_t lastTelemetryMs = 0;
static uint32_t bootMs = 0;
static uint32_t seq = 0;
static bool telemetryEnabled = true;

// ============================================================
// I2C SCAN CACHE
// ============================================================
static uint8_t i2cAddrs[32];
static uint8_t i2cCount = 0;

// ============================================================
// SENSOR DATA (placeholders - no sensors connected)
// ============================================================
struct SensorData {
  bool valid = false;
  float temp_c = NAN;
  float rh_pct = NAN;
  float press_hpa = NAN;
  float gas_ohm = NAN;
  float iaq = NAN;
  float co2eq = NAN;
  float voc_idx = NAN;
};
static SensorData gSensor;

// ============================================================
// LED STATE
// ============================================================
enum LedMode { LED_OFF = 0, LED_STATE = 1, LED_MANUAL = 2, LED_PATTERN = 3 };
enum LedPattern { PAT_SOLID = 0, PAT_BLINK = 1, PAT_BREATHE = 2, PAT_RAINBOW = 3, PAT_CHASE = 4, PAT_SPARKLE = 5 };
static LedMode gLedMode = LED_STATE;
static LedPattern gLedPattern = PAT_SOLID;
static uint8_t gLedR = 0, gLedG = 0, gLedB = 0;
static uint8_t gLedBrightness = 100;  // 0-100 percent

static void ledWriteRGB(uint8_t r, uint8_t g, uint8_t b) {
  // Apply brightness scaling
  uint8_t br = (uint8_t)((r * gLedBrightness) / 100);
  uint8_t bg = (uint8_t)((g * gLedBrightness) / 100);
  uint8_t bb = (uint8_t)((b * gLedBrightness) / 100);
  pixels.setPixelColor(0, pixels.Color(br, bg, bb));
  pixels.show();
}

static void ledOff() { ledWriteRGB(0, 0, 0); }

static void ledBootBlink() {
  for (int i = 0; i < 3; i++) {
    ledWriteRGB(0, 0, 60); delay(60);
    ledWriteRGB(0, 60, 0); delay(60);
    ledWriteRGB(60, 0, 0); delay(60);
    ledOff(); delay(40);
  }
}

static void ledStateUpdate() {
  if (gLedMode == LED_OFF) { ledOff(); return; }
  if (gLedMode == LED_MANUAL) { ledWriteRGB(gLedR, gLedG, gLedB); return; }
  
  uint32_t t = millis();
  
  if (gLedMode == LED_PATTERN) {
    switch (gLedPattern) {
      case PAT_BLINK: {
        bool on = (t / 500) % 2 == 0;
        if (on) ledWriteRGB(gLedR > 0 ? gLedR : 255, gLedG, gLedB);
        else ledOff();
        return;
      }
      case PAT_BREATHE: {
        float phase = sin((double)t / 1000.0) * 0.5 + 0.5;
        ledWriteRGB((uint8_t)((gLedR > 0 ? gLedR : 255) * phase), (uint8_t)(gLedG * phase), (uint8_t)(gLedB * phase));
        return;
      }
      case PAT_RAINBOW: {
        uint8_t hue = (t / 20) % 256;
        uint8_t region = hue / 43;
        uint8_t rem = (hue - (region * 43)) * 6;
        uint8_t q = (255 * (255 - rem)) >> 8;
        uint8_t t2 = (255 * rem) >> 8;
        uint8_t r, g, b;
        switch (region) {
          case 0: r = 255; g = t2; b = 0; break;
          case 1: r = q; g = 255; b = 0; break;
          case 2: r = 0; g = 255; b = t2; break;
          case 3: r = 0; g = q; b = 255; break;
          case 4: r = t2; g = 0; b = 255; break;
          default: r = 255; g = 0; b = q; break;
        }
        ledWriteRGB(r, g, b);
        return;
      }
      case PAT_CHASE: {
        uint8_t phase = (t / 100) % 6;
        uint8_t r = (phase == 0 || phase == 3) ? 255 : 0;
        uint8_t g = (phase == 1 || phase == 4) ? 255 : 0;
        uint8_t b = (phase == 2 || phase == 5) ? 255 : 0;
        ledWriteRGB(r, g, b);
        return;
      }
      case PAT_SPARKLE: {
        if (random(10) == 0) ledWriteRGB(255, 255, 255);
        else ledWriteRGB(gLedR / 4, gLedG / 4, gLedB / 4);
        return;
      }
      default: // PAT_SOLID
        ledWriteRGB(gLedR, gLedG, gLedB);
        return;
    }
  }
  
  // State-based: green pulse when running
  uint8_t v = (uint8_t)(40 + 20 * sin((double)t / 800.0));
  ledWriteRGB(0, v, 0);
}

// ============================================================
// BUZZER
// ============================================================
#define BUZZER_LEDC_RESOLUTION 8
static bool buzzerInitialized = false;

#define BUZZER_LEDC_CHANNEL 0

static void initBuzzer() {
  if (!buzzerInitialized) {
    ledcSetup(BUZZER_LEDC_CHANNEL, 2000, BUZZER_LEDC_RESOLUTION);
    ledcAttachPin(BUZZER_PIN, BUZZER_LEDC_CHANNEL);
    buzzerInitialized = true;
  }
}

static void beep(int freq = 2000, int ms = 50) {
  initBuzzer();
  ledcWriteTone(BUZZER_LEDC_CHANNEL, freq);
  delay(ms);
  ledcWriteTone(BUZZER_LEDC_CHANNEL, 0);
}

static void bootChime() {
  initBuzzer();
  ledcWriteTone(BUZZER_LEDC_CHANNEL, 523); delay(60); ledcWriteTone(BUZZER_LEDC_CHANNEL, 0); delay(10);
  ledcWriteTone(BUZZER_LEDC_CHANNEL, 659); delay(60); ledcWriteTone(BUZZER_LEDC_CHANNEL, 0); delay(10);
  ledcWriteTone(BUZZER_LEDC_CHANNEL, 784); delay(80);
  ledcWriteTone(BUZZER_LEDC_CHANNEL, 0);
}

// ============================================================

// ============================================================
// SOUND PRESETS (Mario-style sounds)
// ============================================================
static void soundCoin() {
  initBuzzer();
  ledcWriteTone(BUZZER_LEDC_CHANNEL, 988); delay(60);
  ledcWriteTone(BUZZER_LEDC_CHANNEL, 1319); delay(120);
  ledcWriteTone(BUZZER_LEDC_CHANNEL, 0);
}

static void soundBump() {
  initBuzzer();
  ledcWriteTone(BUZZER_LEDC_CHANNEL, 200); delay(50);
  ledcWriteTone(BUZZER_LEDC_CHANNEL, 100); delay(50);
  ledcWriteTone(BUZZER_LEDC_CHANNEL, 0);
}

static void soundPower() {
  initBuzzer();
  for (int f = 400; f <= 1200; f += 100) {
    ledcWriteTone(BUZZER_LEDC_CHANNEL, f); delay(25);
  }
  ledcWriteTone(BUZZER_LEDC_CHANNEL, 0);
}

static void sound1up() {
  initBuzzer();
  int notes[] = {330, 392, 523, 392, 523, 659};
  for (int i = 0; i < 6; i++) {
    ledcWriteTone(BUZZER_LEDC_CHANNEL, notes[i]); delay(80);
    ledcWriteTone(BUZZER_LEDC_CHANNEL, 0); delay(20);
  }
}

static void soundMorgio() {
  initBuzzer();
  int notes[] = {659, 659, 0, 659, 0, 523, 659, 0, 784};
  int durs[] = {100, 100, 100, 100, 100, 100, 100, 100, 200};
  for (int i = 0; i < 9; i++) {
    if (notes[i] == 0) ledcWriteTone(BUZZER_LEDC_CHANNEL, 0);
    else ledcWriteTone(BUZZER_LEDC_CHANNEL, notes[i]);
    delay(durs[i]);
  }
  ledcWriteTone(BUZZER_LEDC_CHANNEL, 0);
}

// MAC / NODE ID
// ============================================================
static String getNodeId() {
  uint64_t efuse = ESP.getEfuseMac();
  char buf[24];
  snprintf(buf, sizeof(buf), "A-%02X:%02X:%02X:%02X:%02X:%02X",
    (uint8_t)(efuse >> 40), (uint8_t)(efuse >> 32),
    (uint8_t)(efuse >> 24), (uint8_t)(efuse >> 16),
    (uint8_t)(efuse >> 8), (uint8_t)(efuse));
  return String(buf);
}

static String getMac() {
  uint64_t efuse = ESP.getEfuseMac();
  char buf[18];
  snprintf(buf, sizeof(buf), "%02X:%02X:%02X:%02X:%02X:%02X",
    (uint8_t)(efuse >> 40), (uint8_t)(efuse >> 32),
    (uint8_t)(efuse >> 24), (uint8_t)(efuse >> 16),
    (uint8_t)(efuse >> 8), (uint8_t)(efuse));
  return String(buf);
}

// ============================================================
// OUTPUT HELPERS
// ============================================================
static void writeJson(const JsonDocument& doc) {
  serializeJson(doc, Serial);
  Serial.println();
  Serial.flush();
}

static void writeLine(const char* line) {
  Serial.println(line);
  Serial.flush();
}

static void writeKeyValue(const char* key, const String& value) {
  Serial.print(key);
  Serial.print("=");
  Serial.println(value);
}

static void writeKeyValue(const char* key, int value) {
  Serial.print(key);
  Serial.print("=");
  Serial.println(value);
}

static void writeKeyValue(const char* key, float value) {
  Serial.print(key);
  Serial.print("=");
  Serial.println(value, 2);
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
// COMMAND RESPONSES (dual format)
// ============================================================

static void respondOk(const char* cmdId = nullptr) {
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<128> doc;
    doc["ok"] = true;
    if (cmdId) doc["id"] = cmdId;
    writeJson(doc);
  } else {
    writeLine("ok");
  }
}

static void respondError(const char* msg, const char* cmdId = nullptr) {
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<256> doc;
    doc["ok"] = false;
    doc["error"] = msg;
    if (cmdId) doc["id"] = cmdId;
    writeJson(doc);
  } else {
    Serial.print("error: ");
    Serial.println(msg);
  }
}

static void cmdHelp(const char* cmdId = nullptr) {
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<512> doc;
    doc["ok"] = true;
    if (cmdId) doc["id"] = cmdId;
    JsonArray cmds = doc.createNestedArray("commands");
    cmds.add("help"); cmds.add("status"); cmds.add("ping");
    cmds.add("get_mac"); cmds.add("get_version"); cmds.add("i2c_scan");
    cmds.add("config"); cmds.add("telemetry"); cmds.add("led");
    cmds.add("beep"); cmds.add("fmt"); cmds.add("reboot");
    cmds.add("poster");
    writeJson(doc);
  } else {
    writeLine("=== MycoBrain Side-A Commands ===");
    writeLine("help          - Show this help");
    writeLine("status        - Device status");
    writeLine("ping          - Ping/pong test");
    writeLine("get_mac       - Get MAC address");
    writeLine("get_version   - Firmware version");
    writeLine("i2c / scan    - Scan I2C bus");
    writeLine("config        - Show configuration");
    writeLine("telemetry on/off/period <ms>");
    writeLine("led mode off|state|manual");
    writeLine("led rgb <r> <g> <b>");
    writeLine("beep [freq] [ms]");
    writeLine("fmt json|lines - Set output format");
    writeLine("poster        - Print banner");
    writeLine("reboot        - Restart device");
  }
}

static void cmdStatus(const char* cmdId = nullptr) {
  uint32_t uptime = millis() - bootMs;
  
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<512> doc;
    doc["ok"] = true;
    if (cmdId) doc["id"] = cmdId;
    doc["node_id"] = getNodeId();
    doc["mac"] = getMac();
    doc["uptime_ms"] = uptime;
    doc["uptime_seconds"] = uptime / 1000;
    doc["heap"] = ESP.getFreeHeap();
    doc["firmware_version"] = FW_VERSION;
    doc["telemetry_enabled"] = telemetryEnabled;
    doc["telemetry_interval_ms"] = telemetryIntervalMs;
    doc["i2c_count"] = i2cCount;
    doc["output_format"] = gOutputFormat == FMT_JSON ? "json" : "lines";
    doc["cpu_mhz"] = ESP.getCpuFreqMHz();
    writeJson(doc);
  } else {
    writeLine("=== Status ===");
    writeKeyValue("node_id", getNodeId());
    writeKeyValue("mac", getMac());
    writeKeyValue("uptime_s", (int)(uptime / 1000));
    writeKeyValue("heap", (int)ESP.getFreeHeap());
    writeKeyValue("firmware", FW_VERSION);
    writeKeyValue("telemetry", telemetryEnabled ? "on" : "off");
    writeKeyValue("interval_ms", (int)telemetryIntervalMs);
    writeKeyValue("i2c_count", (int)i2cCount);
    writeKeyValue("cpu_mhz", (int)ESP.getCpuFreqMHz());
  }
}

static void cmdPing(const char* cmdId = nullptr) {
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<128> doc;
    doc["ok"] = true;
    doc["pong"] = true;
    if (cmdId) doc["id"] = cmdId;
    writeJson(doc);
  } else {
    writeLine("pong");
  }
}

static void cmdGetMac(const char* cmdId = nullptr) {
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<256> doc;
    doc["ok"] = true;
    if (cmdId) doc["id"] = cmdId;
    doc["mac"] = getMac();
    doc["node_id"] = getNodeId();
    doc["role"] = "side-a";
    writeJson(doc);
  } else {
    writeKeyValue("mac", getMac());
    writeKeyValue("node_id", getNodeId());
  }
}

static void cmdGetVersion(const char* cmdId = nullptr) {
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<256> doc;
    doc["ok"] = true;
    if (cmdId) doc["id"] = cmdId;
    doc["version"] = FW_VERSION;
    doc["firmware"] = FW_NAME;
    doc["schema_ver"] = SCHEMA_VER;
    doc["build"] = __DATE__ " " __TIME__;
    doc["chip"] = ESP.getChipModel();
    writeJson(doc);
  } else {
    writeKeyValue("version", FW_VERSION);
    writeKeyValue("firmware", FW_NAME);
    writeKeyValue("build", __DATE__ " " __TIME__);
    writeKeyValue("chip", ESP.getChipModel());
  }
}

static void cmdI2cScan(const char* cmdId = nullptr) {
  i2cScan();
  
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<512> doc;
    doc["ok"] = true;
    if (cmdId) doc["id"] = cmdId;
    doc["count"] = i2cCount;
    JsonArray arr = doc.createNestedArray("i2c");
    for (uint8_t i = 0; i < i2cCount; i++) arr.add(i2cAddrs[i]);
    writeJson(doc);
  } else {
    writeLine("I2C scan:");
    if (i2cCount == 0) {
      writeLine("  (none found)");
    } else {
      for (uint8_t i = 0; i < i2cCount; i++) {
        char buf[16];
        snprintf(buf, sizeof(buf), "  found: 0x%02X", i2cAddrs[i]);
        writeLine(buf);
      }
    }
    char countBuf[32];
    snprintf(countBuf, sizeof(countBuf), "count=%d", i2cCount);
    writeLine(countBuf);
  }
}

static void cmdConfig(const char* cmdId = nullptr) {
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<768> doc;
    doc["ok"] = true;
    if (cmdId) doc["id"] = cmdId;
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
    auto timing = doc.createNestedObject("timing");
    timing["telemetry_period_ms"] = telemetryIntervalMs;
    writeJson(doc);
  } else {
    writeLine("=== Config ===");
    writeKeyValue("schema", FW_NAME);
    writeKeyValue("schema_ver", (int)SCHEMA_VER);
    writeKeyValue("node_id", getNodeId());
    writeKeyValue("i2c_sda", PIN_SDA);
    writeKeyValue("i2c_scl", PIN_SCL);
    writeKeyValue("telemetry_ms", (int)telemetryIntervalMs);
  }
}

static void cmdPoster() {
  // Garrett's ASCII banner
  Serial.println();
  Serial.println("====================================================================");
  Serial.println("  MycoBrain Side-A (Dual Mode)");
  Serial.println("  Mycosoft ESP32AB");
  Serial.println("====================================================================");
  Serial.println("   ###############################");
  Serial.println("   #      _   _  ____  ____      #");
  Serial.println("   #     | \\ | ||  _ \\|  _ \\     #");
  Serial.println("   #     |  \\| || |_) | |_) |    #");
  Serial.println("   #     | |\\  ||  __/|  __/     #");
  Serial.println("   #     |_| \\_||_|   |_|        #");
  Serial.println("   ###############################");
  Serial.println("--------------------------------------------------------------------");
  Serial.println("  Commands: help | status | scan | telemetry | led | fmt | reboot");
  Serial.println("  Output: fmt json | fmt lines");
  Serial.println("--------------------------------------------------------------------");
  Serial.println();
}

static void cmdBeep(int freq = 2000, int ms = 100) {
  beep(freq, ms);
  respondOk();
}

static void cmdReboot() {
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<128> doc;
    doc["ok"] = true;
    doc["rebooting"] = true;
    writeJson(doc);
  } else {
    writeLine("rebooting...");
  }
  delay(100);
  ESP.restart();
}

// ============================================================
// TELEMETRY OUTPUT
// ============================================================
static void sendTelemetry() {
  uint32_t t = millis() - bootMs;
  uint32_t uptimeSec = t / 1000;
  
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<768> doc;
    doc["type"] = "tele";
    doc["seq"] = seq++;
    doc["t_ms"] = t;
    doc["node"] = getNodeId();
    doc["uptime_s"] = uptimeSec;
    doc["uptime_seconds"] = uptimeSec;
    
    // Environment (null if no sensors)
    auto env = doc.createNestedObject("env");
    if (gSensor.valid) {
      env["temp_c"] = gSensor.temp_c;
      env["rh_pct"] = gSensor.rh_pct;
      env["press_hpa"] = gSensor.press_hpa;
    } else {
      env["temp_c"] = nullptr;
      env["rh_pct"] = nullptr;
      env["press_hpa"] = nullptr;
    }
    
    // Website-compatible flat fields
    if (gSensor.valid) {
      doc["temperature"] = gSensor.temp_c;
      doc["humidity"] = gSensor.rh_pct;
      doc["pressure"] = gSensor.press_hpa;
      doc["gas_resistance"] = gSensor.gas_ohm;
    } else {
      doc["temperature"] = nullptr;
      doc["humidity"] = nullptr;
      doc["pressure"] = nullptr;
      doc["gas_resistance"] = nullptr;
    }
    
    doc["firmware_version"] = FW_VERSION;
    
    // I2C addresses
    JsonArray i2c = doc.createNestedArray("i2c_addresses");
    for (uint8_t i = 0; i < i2cCount; i++) i2c.add(i2cAddrs[i]);
    
    // Health
    auto health = doc.createNestedObject("health");
    health["heap"] = ESP.getFreeHeap();
    health["i2c_ok"] = (i2cCount > 0);
    
    // Placeholders
    doc["ai1_voltage"] = nullptr;
    doc["ai2_voltage"] = nullptr;
    doc["ai3_voltage"] = nullptr;
    doc["ai4_voltage"] = nullptr;
    JsonArray mosfets = doc.createNestedArray("mosfet_states");
    mosfets.add(false); mosfets.add(false); mosfets.add(false); mosfets.add(false);
    
    writeJson(doc);
  } else {
    // Lines format (like Garrett's live mode)
    Serial.printf("seq=%lu t_ms=%lu uptime=%lu heap=%lu i2c=%d\n",
      seq++, t, uptimeSec, (unsigned long)ESP.getFreeHeap(), i2cCount);
    if (gSensor.valid) {
      Serial.printf("  temp=%.2f rh=%.2f press=%.2f\n",
        gSensor.temp_c, gSensor.rh_pct, gSensor.press_hpa);
    }
  }
}

// ============================================================
// COMMAND PARSER (CLI + JSON)
// ============================================================
static String serialBuffer;

static void parseCliCommand(const String& line) {
  String cmd = line;
  cmd.trim();
  cmd.toLowerCase();
  
  // Extract first word
  int spaceIdx = cmd.indexOf(' ');
  String firstWord = spaceIdx > 0 ? cmd.substring(0, spaceIdx) : cmd;
  String args = spaceIdx > 0 ? cmd.substring(spaceIdx + 1) : "";
  args.trim();
  
  if (firstWord == "help" || firstWord == "?") {
    cmdHelp();
  } else if (firstWord == "status") {
    cmdStatus();
  } else if (firstWord == "ping") {
    cmdPing();
  } else if (firstWord == "get_mac" || firstWord == "mac" || firstWord == "identity") {
    cmdGetMac();
  } else if (firstWord == "get_version" || firstWord == "version" || firstWord == "ver") {
    cmdGetVersion();
  } else if (firstWord == "i2c" || firstWord == "scan" || firstWord == "i2c_scan") {
    cmdI2cScan();
  } else if (firstWord == "config") {
    cmdConfig();
  } else if (firstWord == "poster") {
    cmdPoster();
  } else if (firstWord == "beep") {
    int freq = 2000, ms = 100;
    if (args.length() > 0) {
      int sp = args.indexOf(' ');
      if (sp > 0) {
        freq = args.substring(0, sp).toInt();
        ms = args.substring(sp + 1).toInt();
      } else {
        freq = args.toInt();
      }
    }
    cmdBeep(freq > 0 ? freq : 2000, ms > 0 ? ms : 100);
  // Sound preset CLI commands
  } else if (firstWord == "coin") {
    soundCoin(); respondOk();
  } else if (firstWord == "bump") {
    soundBump(); respondOk();
  } else if (firstWord == "power") {
    soundPower(); respondOk();
  } else if (firstWord == "1up") {
    sound1up(); respondOk();
  } else if (firstWord == "morgio" || firstWord == "melody") {
    soundMorgio(); respondOk();
  } else if (firstWord == "reboot" || firstWord == "restart") {
    cmdReboot();
  } else if (firstWord == "telemetry" || firstWord == "tele") {
    if (args == "on") {
      telemetryEnabled = true;
      respondOk();
    } else if (args == "off") {
      telemetryEnabled = false;
      respondOk();
    } else if (args.startsWith("period ")) {
      uint32_t ms = args.substring(7).toInt();
      if (ms >= 200 && ms <= 60000) {
        telemetryIntervalMs = ms;
        respondOk();
      } else {
        respondError("period must be 200-60000 ms");
      }
    } else {
      // Just show status
      if (gOutputFormat == FMT_JSON) {
        StaticJsonDocument<256> doc;
        doc["ok"] = true;
        doc["enabled"] = telemetryEnabled;
        doc["interval_ms"] = telemetryIntervalMs;
        writeJson(doc);
      } else {
        writeKeyValue("telemetry", telemetryEnabled ? "on" : "off");
        writeKeyValue("interval_ms", (int)telemetryIntervalMs);
      }
    }
  } else if (firstWord == "led") {
    if (args == "off" || args == "mode off") {
      gLedMode = LED_OFF;
      respondOk();
    } else if (args == "state" || args == "mode state") {
      gLedMode = LED_STATE;
      respondOk();
    } else if (args == "manual" || args == "mode manual") {
      gLedMode = LED_MANUAL;
      respondOk();
    } else if (args.startsWith("rgb ")) {
      String rgbArgs = args.substring(4);
      int r = 0, g = 0, b = 0;
      sscanf(rgbArgs.c_str(), "%d %d %d", &r, &g, &b);
      gLedR = constrain(r, 0, 255);
      gLedG = constrain(g, 0, 255);
      gLedB = constrain(b, 0, 255);
      gLedMode = LED_MANUAL;
      respondOk();
    } else if (args.startsWith("brightness ") || args.startsWith("bri ")) {
      int bri = args.substring(args.indexOf(' ') + 1).toInt();
      gLedBrightness = constrain(bri, 0, 100);
      respondOk();
    } else if (args.startsWith("pattern ")) {
      String pat = args.substring(8);
      if (pat == "solid") { gLedPattern = PAT_SOLID; gLedMode = LED_PATTERN; respondOk(); }
      else if (pat == "blink") { gLedPattern = PAT_BLINK; gLedMode = LED_PATTERN; respondOk(); }
      else if (pat == "breathe") { gLedPattern = PAT_BREATHE; gLedMode = LED_PATTERN; respondOk(); }
      else if (pat == "rainbow") { gLedPattern = PAT_RAINBOW; gLedMode = LED_PATTERN; respondOk(); }
      else if (pat == "chase") { gLedPattern = PAT_CHASE; gLedMode = LED_PATTERN; respondOk(); }
      else if (pat == "sparkle") { gLedPattern = PAT_SPARKLE; gLedMode = LED_PATTERN; respondOk(); }
      else { respondError("unknown pattern"); }
    } else {
      respondError("usage: led mode off|state|manual | led rgb r g b | led brightness 0-100 | led pattern solid|blink|breathe|rainbow|chase|sparkle");
    }
  } else if (firstWord == "fmt" || firstWord == "format") {
    if (args == "json" || args == "ndjson") {
      gOutputFormat = FMT_JSON;
      respondOk();
    } else if (args == "lines" || args == "text" || args == "cli") {
      gOutputFormat = FMT_LINES;
      respondOk();
    } else {
      if (gOutputFormat == FMT_JSON) {
        StaticJsonDocument<128> doc;
        doc["ok"] = true;
        doc["format"] = "json";
        writeJson(doc);
      } else {
        writeKeyValue("format", "lines");
      }
    }
  } else if (firstWord.length() > 0) {
    respondError("unknown command - try 'help'");
  }
}

static void parseJsonCommand(const String& line) {
  StaticJsonDocument<512> req;
  DeserializationError err = deserializeJson(req, line);
  if (err) {
    respondError("bad_json");
    return;
  }
  
  // Extract command and ID
  const char* cmd = req["cmd"] | "";
  const char* type = req["type"] | "";
  const char* op = req["op"] | "";
  const char* id = req["id"] | "";
  
  // Workbook format: {"type":"cmd","op":"..."} -> use op as cmd
  if (cmd[0] == '\0' && strcmp(type, "cmd") == 0 && op[0] != '\0')
    cmd = op;
  
  if (cmd[0] == '\0') {
    respondError("missing_cmd", id[0] ? id : nullptr);
    return;
  }
  
  // Route to command handlers
  if (strcmp(cmd, "help") == 0) { cmdHelp(id); }
  else if (strcmp(cmd, "status") == 0 || strcmp(cmd, "status.get") == 0) { cmdStatus(id); }
  else if (strcmp(cmd, "ping") == 0) { cmdPing(id); }
  else if (strcmp(cmd, "get_mac") == 0 || strcmp(cmd, "identity") == 0) { cmdGetMac(id); }
  else if (strcmp(cmd, "get_version") == 0 || strcmp(cmd, "version") == 0) { cmdGetVersion(id); }
  else if (strcmp(cmd, "i2c_scan") == 0 || strcmp(cmd, "i2c.scan") == 0 || strcmp(cmd, "scan") == 0) { cmdI2cScan(id); }
  else if (strcmp(cmd, "config") == 0 || strcmp(cmd, "config.get") == 0) { cmdConfig(id); }
  else if (strcmp(cmd, "beep") == 0) { 
    int freq = req["freq"] | req["frequency"] | 2000;
    int ms = req["ms"] | req["duration"] | 100;
    cmdBeep(freq, ms); 
  }
  // Device manager commands
  else if (strcmp(cmd, "set_buzzer") == 0) {
    if (req.containsKey("off") && req["off"] == true) {
      ledcWriteTone(BUZZER_LEDC_CHANNEL, 0);
      respondOk(id);
    } else {
      int freq = req["frequency"] | 2000;
      int ms = req["duration"] | 100;
      cmdBeep(freq, ms);
    }
  }
  else if (strcmp(cmd, "set_neopixel") == 0) {
    if (req.containsKey("all_off") && req["all_off"] == true) {
      gLedMode = LED_OFF;
      ledOff();
      respondOk(id);
    } else {
      int ledIndex = req["led_index"] | 0;
      if (ledIndex >= 0 && ledIndex < 4) {  // Support 4 LEDs (even if we only have 1 RGB)
        uint8_t r = req["r"] | 0;
        uint8_t g = req["g"] | 0;
        uint8_t b = req["b"] | 0;
        gLedR = r;
        gLedG = g;
        gLedB = b;
        gLedMode = LED_MANUAL;
        ledWriteRGB(r, g, b);
        respondOk(id);
      } else {
        respondError("invalid led_index (0-3)", id);
      }
    }
  }
  else if (strcmp(cmd, "set_mosfet") == 0) {
    // MOSFET control placeholder (no hardware yet)
    int mosfetIndex = req["mosfet_index"] | -1;
    bool state = req.containsKey("state") ? (bool)req["state"] : false;
    if (mosfetIndex >= 0 && mosfetIndex < 4) {
      // TODO: Implement MOSFET control when hardware is available
      StaticJsonDocument<128> doc;
      doc["ok"] = true;
      if (id[0]) doc["id"] = id;
      doc["mosfet_index"] = mosfetIndex;
      doc["state"] = state;
      doc["note"] = "MOSFET control not yet implemented";
      writeJson(doc);
    } else {
      respondError("invalid mosfet_index (0-3)", id);
    }
  }
  else if (strcmp(cmd, "reboot") == 0 || strcmp(cmd, "restart") == 0) { cmdReboot(); }
  else if (strcmp(cmd, "set_telemetry_interval") == 0 || strcmp(cmd, "telemetry.period") == 0) {
    uint32_t ms = req["ms"] | (req["period_ms"] | telemetryIntervalMs);
    if (ms >= 200 && ms <= 60000) {
      telemetryIntervalMs = ms;
      StaticJsonDocument<192> doc;
      doc["ok"] = true;
      if (id[0]) doc["id"] = id;
      doc["telemetry_interval_ms"] = telemetryIntervalMs;
      writeJson(doc);
    } else {
      respondError("period must be 200-60000 ms", id);
    }
  }
  else if (strcmp(cmd, "telemetry.on") == 0) { telemetryEnabled = true; respondOk(id); }
  else if (strcmp(cmd, "telemetry.off") == 0) { telemetryEnabled = false; respondOk(id); }
  else if (strcmp(cmd, "led") == 0 || strcmp(cmd, "led.set") == 0) {
    const char* mode = req["mode"] | "";
    if (strcmp(mode, "off") == 0) gLedMode = LED_OFF;
    else if (strcmp(mode, "state") == 0) gLedMode = LED_STATE;
    else if (strcmp(mode, "manual") == 0) gLedMode = LED_MANUAL;
    if (req.containsKey("r") || req.containsKey("g") || req.containsKey("b")) {
      gLedR = req["r"] | gLedR;
      gLedG = req["g"] | gLedG;
      gLedB = req["b"] | gLedB;
      gLedMode = LED_MANUAL;
    }
    respondOk(id);
  }
  else if (strcmp(cmd, "fmt") == 0 || strcmp(cmd, "format") == 0) {
    const char* fmt = req["format"] | "";
    if (strcmp(fmt, "json") == 0) gOutputFormat = FMT_JSON;
    else if (strcmp(fmt, "lines") == 0) gOutputFormat = FMT_LINES;
    respondOk(id);
  }
  else {
    respondError("unknown_cmd", id);
  }
}

static void processSerialInput() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0) {
        serialBuffer.trim();
        
        // Detect format: JSON starts with '{'
        if (serialBuffer.startsWith("{")) {
          parseJsonCommand(serialBuffer);
        } else {
          parseCliCommand(serialBuffer);
        }
        serialBuffer = "";
      }
    } else {
      serialBuffer += c;
      if (serialBuffer.length() > 2048) serialBuffer = "";
    }
  }
}

// ============================================================
// SETUP
// ============================================================
void setup() {
  // Disable brownout for bridged board
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  
  Serial.begin(SERIAL_BAUD);
  
  // Boot wait for USB CDC (Garrett's approach)
  delay(BOOT_WAIT_MS);
  
  // Initialize Adafruit NeoPixel for SK6805 on GPIO15 (like Chris's original)
  pixels.begin();
  pixels.setBrightness(50);
  pixels.clear();
  pixels.show();
  
  bootMs = millis();
  
  // Initialize I2C
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(I2C_FREQ);
  
  // Initialize LED pins
  for (int i = 0; i < 3; i++) pinMode(AO_PINS[i], OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  
  // Boot sequence
  ledBootBlink();
  bootChime();
  
  // Initial I2C scan
  i2cScan();
  
  // Print banner
  cmdPoster();
  
  // Print boot message (JSON)
  {
    StaticJsonDocument<384> hello;
    hello["type"] = "boot";
    hello["ok"] = true;
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
    hello["output_format"] = "json";
    writeJson(hello);
  }
}

// ============================================================
// LOOP
// ============================================================
void loop() {
  yield();
  
  // Process commands
  processSerialInput();
  
  // Update LED state machine
  ledStateUpdate();
  
  // Periodic telemetry
  if (telemetryEnabled) {
    uint32_t now = millis();
    if (now - lastTelemetryMs >= telemetryIntervalMs) {
      lastTelemetryMs = now;
      sendTelemetry();
    }
  }
}


