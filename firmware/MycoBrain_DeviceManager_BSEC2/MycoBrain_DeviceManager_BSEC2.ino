/*
 * MycoBrain DeviceManager + BSEC2 Hybrid Firmware
 * 
 * Combines:
 *   - BSEC2 library for IAQ, CO2eq, VOC, gas classification (from Garret's working code)
 *   - NeoPixel on GPIO15 (SK6805) using Adafruit_NeoPixel
 *   - LEDC buzzer on GPIO16
 *   - Optical/Acoustic modem TX
 *   - Dual-mode CLI + JSON commands
 * 
 * Arduino IDE Settings (ESP32-S3 Dev Module):
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
#include "bsec2.h"

// Brownout disable for bridged board
#include "soc/rtc_cntl_reg.h"

#ifndef ARRAY_LEN
  #define ARRAY_LEN(x) (sizeof(x) / sizeof((x)[0]))
#endif

// ============================================================
// BSEC2 CONFIG BLOB (optional external selectivity config)
// ============================================================
#define USE_EXTERNAL_BLOB 0  // Set to 1 when you have a compatible selectivity blob from Bosch BME AI Studio

#if USE_EXTERNAL_BLOB
  #include "bsec_selectivity.h"
  static const uint8_t*  CFG_PTR = bsec_selectivity_config;
  static const uint32_t  CFG_LEN = (uint32_t)bsec_selectivity_config_len;
#else
  static const uint8_t*  CFG_PTR = nullptr;
  static const uint32_t  CFG_LEN = 0;
#endif

// ============================================================
// PIN CONFIGURATION
// ============================================================
static const uint8_t PIN_SDA = 5;
static const uint8_t PIN_SCL = 4;
static const uint32_t I2C_FREQ = 100000;

// NeoPixel on GPIO15 (SK6805)
#define NEOPIXEL_PIN 15
#define PIXEL_COUNT 1
Adafruit_NeoPixel pixels(PIXEL_COUNT, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);

// Buzzer on GPIO16
static const uint8_t BUZZER_PIN = 16;

// MOSFET outputs (for future use)
static const uint8_t AO_PINS[3] = {12, 13, 14};

// ============================================================
// FIRMWARE INFO
// ============================================================
static const char* FW_NAME = "mycobrain.sideA.bsec2";
static const char* FW_VERSION = "2.0.0";
static const uint32_t SCHEMA_VER = 4;

// ============================================================
// OUTPUT FORMAT
// ============================================================
enum OutputFormat { FMT_JSON = 0, FMT_LINES = 1 };
static OutputFormat gOutputFormat = FMT_JSON;

// ============================================================
// TIMING
// ============================================================
static const uint32_t SERIAL_BAUD = 115200;
static const uint32_t BOOT_WAIT_MS = 1800;
static uint32_t telemetryIntervalMs = 2000;
static uint32_t lastTelemetryMs = 0;
static uint32_t bootMs = 0;
static uint32_t seq = 0;
static bool telemetryEnabled = true;

// ============================================================
// BSEC2 SENSOR STRUCTURES (from Garret's working code)
// ============================================================
struct AmbReading {
  bool valid = false;
  uint32_t t_ms = 0;
  float tC = NAN;
  float rh = NAN;
  float p_raw = NAN;
  float p_hPa = NAN;
  float gas_ohm = NAN;
  float iaq = NAN;
  float iaqAccuracy = NAN;
  float staticIaq = NAN;
  float co2eq = NAN;
  float voc = NAN;
  float gasClass = NAN;
  float gasProb = NAN;
};

struct SensorSlot {
  const char* name = nullptr;
  uint8_t addr = 0;
  bool present = false;
  Bsec2 bsec;
  uint8_t mem[BSEC_INSTANCE_SIZE];
  bool beginOk = false;
  bool subOk = false;
  bool cfgOk = false;
  int lastStatus = 0;
  float sampleRate = BSEC_SAMPLE_RATE_LP;
  AmbReading r;
  
  void init(const char* n, uint8_t a) {
    name = n;
    addr = a;
  }
};

// Two sensor slots: AMB at 0x77, ENV at 0x76
static SensorSlot S_AMB;
static SensorSlot S_ENV;

static uint8_t bme688_count = 0;

// ============================================================
// LED STATE
// ============================================================
enum LedMode { LED_OFF = 0, LED_STATE = 1, LED_MANUAL = 2, LED_PATTERN = 3 };
enum LedPattern { PAT_SOLID = 0, PAT_BLINK = 1, PAT_BREATHE = 2, PAT_RAINBOW = 3, PAT_CHASE = 4, PAT_SPARKLE = 5 };
static LedMode gLedMode = LED_STATE;
static LedPattern gLedPattern = PAT_SOLID;
static uint8_t gLedR = 0, gLedG = 0, gLedB = 0;
static uint8_t gLedBrightness = 100;

static void ledWriteRGB(uint8_t r, uint8_t g, uint8_t b) {
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
      default:
        ledWriteRGB(gLedR, gLedG, gLedB);
        return;
    }
  }
  
  // State-based: Color based on sensor status (from Garret)
  const bool anyPresent = S_AMB.present || S_ENV.present;
  const bool anyData = (S_AMB.present && S_AMB.r.valid) || (S_ENV.present && S_ENV.r.valid);
  const bool anyBeginFail = (S_AMB.present && !S_AMB.beginOk) || (S_ENV.present && !S_ENV.beginOk);
  const bool anySubFail = (S_AMB.present && S_AMB.beginOk && !S_AMB.subOk) || (S_ENV.present && S_ENV.beginOk && !S_ENV.subOk);
  
  if (!anyPresent) {
    uint8_t v = (uint8_t)(20 + (t / 6) % 80);
    ledWriteRGB(v, 0, 0);  // Red pulse: no sensors
  } else if (anyBeginFail) {
    bool on = ((t / 250) % 2) == 0;
    ledWriteRGB(on ? 120 : 0, 0, 0);  // Blinking red: begin failed
  } else if (!anyData) {
    uint8_t v = (uint8_t)(30 + (t / 8) % 90);
    ledWriteRGB(0, 0, v);  // Blue: initializing
  } else if (anySubFail) {
    ledWriteRGB(80, 60, 0);  // Yellow: subscription failed
  } else {
    ledWriteRGB(0, 90, 0);  // Green: all good
  }
}

// ============================================================
// BUZZER (LEDC-based for ESP32-S3)
// ============================================================
#define BUZZER_LEDC_CHANNEL 0
#define BUZZER_LEDC_RESOLUTION 8
static bool buzzerInitialized = false;

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

// Sound presets
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

// ============================================================
// OPTICAL MODEM TX
// ============================================================
enum OptxMode { OPTX_IDLE = 0, OPTX_OOK = 1, OPTX_MANCHESTER = 2 };
static OptxMode gOptxMode = OPTX_IDLE;
static String gOptxPayload = "";
static uint32_t gOptxRateHz = 10;
static uint32_t gOptxRepeat = 1;
static uint32_t gOptxBitIndex = 0;
static uint32_t gOptxRepeatCount = 0;
static uint32_t gOptxLastSymbol = 0;
static uint8_t gOptxSavedR = 0, gOptxSavedG = 0, gOptxSavedB = 0;

static void optxStart(const String& profile, const String& payload, uint32_t rateHz, uint32_t repeat) {
  gOptxSavedR = gLedR; gOptxSavedG = gLedG; gOptxSavedB = gLedB;
  if (profile == "manchester") gOptxMode = OPTX_MANCHESTER;
  else gOptxMode = OPTX_OOK;
  gOptxPayload = payload;
  gOptxRateHz = constrain(rateHz, 1, 100);
  gOptxRepeat = constrain(repeat, 1, 100);
  gOptxBitIndex = 0;
  gOptxRepeatCount = 0;
  gOptxLastSymbol = 0;
  gLedMode = LED_MANUAL;
}

static void optxStop() {
  gOptxMode = OPTX_IDLE;
  gLedR = gOptxSavedR; gLedG = gOptxSavedG; gLedB = gOptxSavedB;
  ledWriteRGB(gLedR, gLedG, gLedB);
}

static void optxUpdate() {
  if (gOptxMode == OPTX_IDLE) return;
  if (gOptxPayload.length() == 0) { optxStop(); return; }
  uint32_t now = millis();
  uint32_t symbolPeriod = 1000 / gOptxRateHz;
  if (now - gOptxLastSymbol >= symbolPeriod) {
    gOptxLastSymbol = now;
    uint32_t totalBits = gOptxPayload.length() * 8;
    if (gOptxBitIndex >= totalBits) {
      gOptxRepeatCount++;
      if (gOptxRepeatCount >= gOptxRepeat) { optxStop(); return; }
      gOptxBitIndex = 0;
    }
    uint32_t byteIndex = gOptxBitIndex / 8;
    uint32_t bitInByte = 7 - (gOptxBitIndex % 8);
    uint8_t byte = gOptxPayload[byteIndex];
    bool bit = (byte >> bitInByte) & 1;
    if (bit) ledWriteRGB(255, 255, 255);
    else ledWriteRGB(0, 0, 0);
    gOptxBitIndex++;
  }
}

// ============================================================
// ACOUSTIC MODEM TX
// ============================================================
enum AotxMode { AOTX_IDLE = 0, AOTX_FSK = 1 };
static AotxMode gAotxMode = AOTX_IDLE;
static String gAotxPayload = "";
static uint32_t gAotxSymbolMs = 100;
static uint32_t gAotxF0 = 1000;
static uint32_t gAotxF1 = 2000;
static uint32_t gAotxRepeat = 1;
static uint32_t gAotxBitIndex = 0;
static uint32_t gAotxRepeatCount = 0;
static uint32_t gAotxSymbolStart = 0;

static void aotxStart(const String& payload, uint32_t symbolMs, uint32_t f0, uint32_t f1, uint32_t repeat) {
  gAotxMode = AOTX_FSK;
  gAotxPayload = payload;
  gAotxSymbolMs = constrain(symbolMs, 10, 1000);
  gAotxF0 = constrain(f0, 100, 10000);
  gAotxF1 = constrain(f1, 100, 10000);
  gAotxRepeat = constrain(repeat, 1, 100);
  gAotxBitIndex = 0;
  gAotxRepeatCount = 0;
  gAotxSymbolStart = 0;
  initBuzzer();
}

static void aotxStop() {
  gAotxMode = AOTX_IDLE;
  ledcWriteTone(BUZZER_LEDC_CHANNEL, 0);
}

static void aotxUpdate() {
  if (gAotxMode == AOTX_IDLE) return;
  if (gAotxPayload.length() == 0) { aotxStop(); return; }
  uint32_t now = millis();
  if (now - gAotxSymbolStart >= gAotxSymbolMs) {
    gAotxSymbolStart = now;
    uint32_t totalBits = gAotxPayload.length() * 8;
    if (gAotxBitIndex >= totalBits) {
      gAotxRepeatCount++;
      if (gAotxRepeatCount >= gAotxRepeat) { aotxStop(); return; }
      gAotxBitIndex = 0;
    }
    uint32_t byteIndex = gAotxBitIndex / 8;
    uint32_t bitInByte = 7 - (gAotxBitIndex % 8);
    uint8_t byte = gAotxPayload[byteIndex];
    bool bit = (byte >> bitInByte) & 1;
    ledcWriteTone(BUZZER_LEDC_CHANNEL, bit ? gAotxF1 : gAotxF0);
    gAotxBitIndex++;
  }
}

// ============================================================
// I2C HELPERS
// ============================================================
static uint8_t i2cAddrs[32];
static uint8_t i2cCount = 0;

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

static float pressureToHpa(float p) {
  if (!isfinite(p) || p <= 0) return NAN;
  if (p > 20000.0f) return p / 100.0f;
  if (p > 2000.0f) return p / 10.0f;
  if (p > 200.0f) return p;
  if (p > 20.0f) return p * 10.0f;
  return p * 1000.0f;
}

// ============================================================
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
  Serial.print(key); Serial.print("="); Serial.println(value);
}

static void writeKeyValue(const char* key, int value) {
  Serial.print(key); Serial.print("="); Serial.println(value);
}

// ============================================================
// BSEC2 CALLBACKS
// ============================================================
static void slotCallbackCommon(SensorSlot &s, const bme68xData data, const bsecOutputs outputs) {
  s.r.valid = true;
  s.r.t_ms = millis();
  s.r.tC = data.temperature;
  s.r.rh = data.humidity;
  s.r.p_raw = (float)data.pressure;
  s.r.p_hPa = pressureToHpa(s.r.p_raw);
  s.r.gas_ohm = (float)data.gas_resistance;

  s.r.iaq = NAN;
  s.r.iaqAccuracy = NAN;
  s.r.staticIaq = NAN;
  s.r.co2eq = NAN;
  s.r.voc = NAN;
  s.r.gasClass = NAN;
  s.r.gasProb = NAN;

  for (uint8_t i = 0; i < outputs.nOutputs; i++) {
    const bsecData &o = outputs.output[i];
    switch (o.sensor_id) {
      case BSEC_OUTPUT_IAQ:
        s.r.iaq = o.signal;
        s.r.iaqAccuracy = (float)o.accuracy;
        break;
      case BSEC_OUTPUT_STATIC_IAQ:
        s.r.staticIaq = o.signal;
        break;
      case BSEC_OUTPUT_CO2_EQUIVALENT:
        s.r.co2eq = o.signal;
        break;
      case BSEC_OUTPUT_BREATH_VOC_EQUIVALENT:
        s.r.voc = o.signal;
        break;
      case BSEC_OUTPUT_GAS_ESTIMATE_1:
      case BSEC_OUTPUT_GAS_ESTIMATE_2:
      case BSEC_OUTPUT_GAS_ESTIMATE_3:
      case BSEC_OUTPUT_GAS_ESTIMATE_4:
        if (o.signal > 0.1f) {
          s.r.gasClass = (float)(o.sensor_id - BSEC_OUTPUT_GAS_ESTIMATE_1);
          s.r.gasProb = o.signal;
        }
        break;
      default:
        break;
    }
  }
}

static void cbAMB(const bme68xData data, const bsecOutputs outputs, const Bsec2 /*bsec*/) {
  slotCallbackCommon(S_AMB, data, outputs);
}

static void cbENV(const bme68xData data, const bsecOutputs outputs, const Bsec2 /*bsec*/) {
  slotCallbackCommon(S_ENV, data, outputs);
}

// ============================================================
// BSEC2 SENSOR INITIALIZATION
// ============================================================
static bool slotInit(SensorSlot &s) {
  s.present = false;
  s.beginOk = s.subOk = s.cfgOk = false;
  s.lastStatus = 0;
  s.r = AmbReading();

  Wire.beginTransmission(s.addr);
  if (Wire.endTransmission() != 0) {
    Serial.printf("[%s] not found @ 0x%02X\n", s.name, s.addr);
    return false;
  }
  s.present = true;

  s.bsec.allocateMemory(s.mem);

  Serial.printf("[%s] begin(0x%02X)...\n", s.name, s.addr);
  if (!s.bsec.begin(s.addr, Wire)) {
    Serial.printf("[%s] begin FAILED\n", s.name);
    s.lastStatus = (int)s.bsec.status;
    return false;
  }
  s.beginOk = true;
  Serial.printf("[%s] begin OK\n", s.name);

  s.bsec.setTemperatureOffset(0.0f);

  if (CFG_PTR && CFG_LEN) {
    Serial.printf("[%s] setConfig(blob %lu bytes)...\n", s.name, (unsigned long)CFG_LEN);
    if (!s.bsec.setConfig(CFG_PTR)) {
      Serial.printf("[%s] setConfig FAILED\n", s.name);
      s.cfgOk = false;
    } else {
      Serial.printf("[%s] setConfig OK\n", s.name);
      s.cfgOk = true;
    }
  }

  if (s.addr == 0x77) s.bsec.attachCallback(cbAMB);
  if (s.addr == 0x76) s.bsec.attachCallback(cbENV);

  // BSEC2 outputs - includes gas classification when selectivity blob is present
  bsecSensor list[] = {
    BSEC_OUTPUT_IAQ,
    BSEC_OUTPUT_STATIC_IAQ,
    BSEC_OUTPUT_CO2_EQUIVALENT,
    BSEC_OUTPUT_BREATH_VOC_EQUIVALENT,
#if USE_EXTERNAL_BLOB
    BSEC_OUTPUT_GAS_ESTIMATE_1,
    BSEC_OUTPUT_GAS_ESTIMATE_2,
    BSEC_OUTPUT_GAS_ESTIMATE_3,
    BSEC_OUTPUT_GAS_ESTIMATE_4
#endif
  };

  Serial.printf("[%s] updateSubscription(LP, %d outputs)...\n", s.name, (int)ARRAY_LEN(list));
  if (s.bsec.updateSubscription(list, (uint8_t)ARRAY_LEN(list), s.sampleRate)) {
    Serial.printf("[%s] updateSubscription OK\n", s.name);
    s.subOk = true;
  } else {
    Serial.printf("[%s] updateSubscription FAILED\n", s.name);
    s.subOk = false;
  }

  return true;
}

static void initAllSensors() {
  Wire.end();
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(I2C_FREQ);

  Serial.printf("I2C: SDA=%d SCL=%d @ %lu Hz\n", PIN_SDA, PIN_SCL, (unsigned long)I2C_FREQ);
  i2cScan();

  slotInit(S_AMB);
  slotInit(S_ENV);

  bme688_count = (S_AMB.present ? 1 : 0) + (S_ENV.present ? 1 : 0);
  Serial.printf("BME688 count: %d\n", bme688_count);
}

// ============================================================
// COMMAND RESPONSES
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
    Serial.print("error: "); Serial.println(msg);
  }
}

static void cmdOptxStatus(const char* cmdId = nullptr) {
  StaticJsonDocument<256> doc;
  doc["ok"] = true;
  if (cmdId) doc["id"] = cmdId;
  doc["running"] = (gOptxMode != OPTX_IDLE);
  doc["mode"] = gOptxMode == OPTX_OOK ? "ook" : (gOptxMode == OPTX_MANCHESTER ? "manchester" : "idle");
  doc["bit_index"] = gOptxBitIndex;
  doc["repeat_count"] = gOptxRepeatCount;
  writeJson(doc);
}

static void cmdAotxStatus(const char* cmdId = nullptr) {
  StaticJsonDocument<256> doc;
  doc["ok"] = true;
  if (cmdId) doc["id"] = cmdId;
  doc["running"] = (gAotxMode != AOTX_IDLE);
  doc["mode"] = gAotxMode == AOTX_FSK ? "fsk" : "idle";
  doc["bit_index"] = gAotxBitIndex;
  doc["f0"] = gAotxF0;
  doc["f1"] = gAotxF1;
  writeJson(doc);
}

// ============================================================
// SENSOR OUTPUT
// ============================================================
static void printOneSensorJson(const SensorSlot &s, JsonObject &obj) {
  obj["address"] = s.addr;
  obj["label"] = s.name;
  obj["present"] = s.present;
  obj["beginOk"] = s.beginOk;
  obj["subOk"] = s.subOk;
  
  if (s.r.valid) {
    obj["temp_c"] = s.r.tC;
    obj["humidity_pct"] = s.r.rh;
    obj["pressure_hpa"] = s.r.p_hPa;
    obj["gas_ohm"] = s.r.gas_ohm;
    
    if (!isnan(s.r.iaq)) {
      obj["iaq"] = s.r.iaq;
      obj["iaq_accuracy"] = (int)s.r.iaqAccuracy;
    }
    if (!isnan(s.r.staticIaq)) obj["static_iaq"] = s.r.staticIaq;
    if (!isnan(s.r.co2eq)) obj["co2_equivalent"] = s.r.co2eq;
    if (!isnan(s.r.voc)) obj["voc_equivalent"] = s.r.voc;
    if (!isnan(s.r.gasClass)) {
      obj["gas_class"] = (int)s.r.gasClass;
      obj["gas_probability"] = s.r.gasProb;
    }
  }
}

static void cmdSensors(const char* cmdId = nullptr) {
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<1024> doc;
    doc["ok"] = true;
    if (cmdId) doc["id"] = cmdId;
    doc["bme688_count"] = bme688_count;
    
    if (S_AMB.present) {
      JsonObject s1 = doc.createNestedObject("bme1");
      printOneSensorJson(S_AMB, s1);
    }
    
    if (S_ENV.present) {
      JsonObject s2 = doc.createNestedObject("bme2");
      printOneSensorJson(S_ENV, s2);
    }
    
    if (!S_AMB.present && !S_ENV.present) {
      doc["message"] = "No BME688 sensors detected";
    }
    writeJson(doc);
  } else {
    writeLine("BME688 Sensors (BSEC2):");
    if (!S_AMB.present && !S_ENV.present) {
      writeLine("  No sensors detected");
    } else {
      if (S_AMB.present && S_AMB.r.valid) {
        Serial.printf("  AMB 0x77: T=%.2fC H=%.1f%% P=%.1fhPa IAQ=%.0f CO2=%.0f VOC=%.2f\n",
          S_AMB.r.tC, S_AMB.r.rh, S_AMB.r.p_hPa, S_AMB.r.iaq, S_AMB.r.co2eq, S_AMB.r.voc);
      }
      if (S_ENV.present && S_ENV.r.valid) {
        Serial.printf("  ENV 0x76: T=%.2fC H=%.1f%% P=%.1fhPa IAQ=%.0f CO2=%.0f VOC=%.2f\n",
          S_ENV.r.tC, S_ENV.r.rh, S_ENV.r.p_hPa, S_ENV.r.iaq, S_ENV.r.co2eq, S_ENV.r.voc);
      }
    }
  }
}

static void cmdStatus(const char* cmdId = nullptr) {
  uint32_t uptime = millis() - bootMs;
  
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<768> doc;
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
    doc["bme688_count"] = bme688_count;
    doc["i2c_count"] = i2cCount;
    doc["output_format"] = gOutputFormat == FMT_JSON ? "json" : "lines";
    doc["cpu_mhz"] = ESP.getCpuFreqMHz();
    doc["bsec2"] = true;
    writeJson(doc);
  } else {
    writeLine("=== Status (BSEC2) ===");
    writeKeyValue("node_id", getNodeId());
    writeKeyValue("mac", getMac());
    writeKeyValue("uptime_s", (int)(uptime / 1000));
    writeKeyValue("heap", (int)ESP.getFreeHeap());
    writeKeyValue("firmware", FW_VERSION);
    writeKeyValue("bme688_count", (int)bme688_count);
    writeKeyValue("i2c_count", (int)i2cCount);
    writeKeyValue("cpu_mhz", (int)ESP.getCpuFreqMHz());
  }
}

static void cmdI2cScan(const char* cmdId = nullptr) {
  i2cScan();
  initAllSensors();
  
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<512> doc;
    doc["ok"] = true;
    if (cmdId) doc["id"] = cmdId;
    doc["count"] = i2cCount;
    doc["bme688_count"] = bme688_count;
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
  }
}

static void cmdHelp(const char* cmdId = nullptr) {
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<512> doc;
    doc["ok"] = true;
    if (cmdId) doc["id"] = cmdId;
    JsonArray cmds = doc.createNestedArray("commands");
    cmds.add("help"); cmds.add("status"); cmds.add("ping");
    cmds.add("get_mac"); cmds.add("get_version"); cmds.add("scan");
    cmds.add("sensors"); cmds.add("led"); cmds.add("beep");
    cmds.add("fmt"); cmds.add("optx"); cmds.add("aotx"); cmds.add("reboot");
    writeJson(doc);
  } else {
    writeLine("=== MycoBrain BSEC2 Commands ===");
    writeLine("help/status/ping/get_mac/get_version");
    writeLine("scan - I2C scan + reinit sensors");
    writeLine("sensors - BME688 data with IAQ/CO2/VOC");
    writeLine("led mode off|state|manual | led rgb r g b");
    writeLine("led brightness 0-100 | led pattern ...");
    writeLine("beep [freq] [ms] | coin | bump | power | 1up | morgio");
    writeLine("optx start/stop/status | aotx start/stop/status");
    writeLine("fmt json|lines | reboot");
  }
}

static void cmdPoster() {
  Serial.println();
  Serial.println("====================================================================");
  Serial.println("  MycoBrain DeviceManager + BSEC2");
  Serial.println("  Mycosoft ESP32AB");
  Serial.println("====================================================================");
  Serial.println("   IAQ | CO2eq | VOC | Gas Classification");
  Serial.println("   NeoPixel GPIO15 | LEDC Buzzer GPIO16");
  Serial.println("   Optical TX | Acoustic TX");
  Serial.println("--------------------------------------------------------------------");
  Serial.println("  Commands: help | status | sensors | scan | led | beep | fmt");
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
  
  if (gOutputFormat == FMT_JSON) {
    StaticJsonDocument<1024> doc;
    doc["type"] = "tele";
    doc["seq"] = seq++;
    doc["t_ms"] = t;
    doc["node"] = getNodeId();
    doc["uptime_s"] = t / 1000;
    doc["uptime_seconds"] = t / 1000;
    doc["bme688_count"] = bme688_count;
    
    // Primary sensor data (use AMB if available, else ENV)
    SensorSlot* primary = S_AMB.present ? &S_AMB : (S_ENV.present ? &S_ENV : nullptr);
    if (primary && primary->r.valid) {
      doc["temperature"] = primary->r.tC;
      doc["humidity"] = primary->r.rh;
      doc["pressure"] = primary->r.p_hPa;
      doc["gas_resistance"] = primary->r.gas_ohm;
      if (!isnan(primary->r.iaq)) {
        doc["iaq"] = primary->r.iaq;
        doc["iaq_accuracy"] = (int)primary->r.iaqAccuracy;
      }
      if (!isnan(primary->r.co2eq)) doc["co2_equivalent"] = primary->r.co2eq;
      if (!isnan(primary->r.voc)) doc["voc_equivalent"] = primary->r.voc;
      if (!isnan(primary->r.gasClass)) {
        doc["gas_class"] = (int)primary->r.gasClass;
        doc["gas_probability"] = primary->r.gasProb;
      }
    }
    
    doc["firmware_version"] = FW_VERSION;
    
    auto health = doc.createNestedObject("health");
    health["heap"] = ESP.getFreeHeap();
    health["i2c_ok"] = (i2cCount > 0);
    
    writeJson(doc);
  } else {
    Serial.printf("seq=%lu uptime=%lu heap=%lu\n", seq++, t / 1000, (unsigned long)ESP.getFreeHeap());
    if (S_AMB.present && S_AMB.r.valid) {
      Serial.printf("  AMB: T=%.2f RH=%.2f IAQ=%.0f CO2=%.0f VOC=%.2f\n",
        S_AMB.r.tC, S_AMB.r.rh, S_AMB.r.iaq, S_AMB.r.co2eq, S_AMB.r.voc);
    }
    if (S_ENV.present && S_ENV.r.valid) {
      Serial.printf("  ENV: T=%.2f RH=%.2f IAQ=%.0f CO2=%.0f VOC=%.2f\n",
        S_ENV.r.tC, S_ENV.r.rh, S_ENV.r.iaq, S_ENV.r.co2eq, S_ENV.r.voc);
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
  
  int spaceIdx = cmd.indexOf(' ');
  String firstWord = spaceIdx > 0 ? cmd.substring(0, spaceIdx) : cmd;
  String args = spaceIdx > 0 ? cmd.substring(spaceIdx + 1) : "";
  args.trim();
  
  if (firstWord == "help" || firstWord == "?") { cmdHelp(); }
  else if (firstWord == "status") { cmdStatus(); }
  else if (firstWord == "ping") { respondOk(); }
  else if (firstWord == "get_mac" || firstWord == "mac") {
    if (gOutputFormat == FMT_JSON) {
      StaticJsonDocument<256> doc;
      doc["ok"] = true;
      doc["mac"] = getMac();
      doc["node_id"] = getNodeId();
      writeJson(doc);
    } else {
      writeKeyValue("mac", getMac());
    }
  }
  else if (firstWord == "get_version" || firstWord == "version" || firstWord == "ver") {
    if (gOutputFormat == FMT_JSON) {
      StaticJsonDocument<256> doc;
      doc["ok"] = true;
      doc["version"] = FW_VERSION;
      doc["firmware"] = FW_NAME;
      doc["bsec2"] = true;
      writeJson(doc);
    } else {
      writeKeyValue("version", FW_VERSION);
    }
  }
  else if (firstWord == "scan" || firstWord == "i2c" || firstWord == "i2c_scan") { cmdI2cScan(); }
  else if (firstWord == "sensors" || firstWord == "bme" || firstWord == "bme688") { cmdSensors(); }
  else if (firstWord == "poster") { cmdPoster(); }
  else if (firstWord == "beep") {
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
  }
  else if (firstWord == "coin") { soundCoin(); respondOk(); }
  else if (firstWord == "bump") { soundBump(); respondOk(); }
  else if (firstWord == "power") { soundPower(); respondOk(); }
  else if (firstWord == "1up") { sound1up(); respondOk(); }
  else if (firstWord == "morgio" || firstWord == "melody") { soundMorgio(); respondOk(); }
  else if (firstWord == "reboot" || firstWord == "restart") { cmdReboot(); }
  else if (firstWord == "telemetry" || firstWord == "tele") {
    if (args == "on") { telemetryEnabled = true; respondOk(); }
    else if (args == "off") { telemetryEnabled = false; respondOk(); }
    else if (args.startsWith("period ")) {
      uint32_t ms = args.substring(7).toInt();
      if (ms >= 200 && ms <= 60000) {
        telemetryIntervalMs = ms;
        respondOk();
      } else {
        respondError("period must be 200-60000 ms");
      }
    } else {
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
  }
  else if (firstWord == "led") {
    if (args == "off" || args == "mode off") {
      gLedMode = LED_OFF; respondOk();
    } else if (args == "state" || args == "mode state") {
      gLedMode = LED_STATE; respondOk();
    } else if (args == "manual" || args == "mode manual") {
      gLedMode = LED_MANUAL; respondOk();
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
      respondError("usage: led mode off|state|manual | led rgb r g b");
    }
  }
  else if (firstWord == "fmt" || firstWord == "format") {
    if (args == "json" || args == "ndjson") { gOutputFormat = FMT_JSON; respondOk(); }
    else if (args == "lines" || args == "text" || args == "cli") { gOutputFormat = FMT_LINES; respondOk(); }
    else {
      if (gOutputFormat == FMT_JSON) {
        StaticJsonDocument<128> doc;
        doc["ok"] = true;
        doc["format"] = "json";
        writeJson(doc);
      } else {
        writeKeyValue("format", "lines");
      }
    }
  }
  else if (firstWord == "optx") {
    if (args.startsWith("start ")) {
      String payload = args.substring(6);
      optxStart("ook", payload, 10, 1);
      respondOk();
    } else if (args == "stop") {
      optxStop();
      respondOk();
    } else if (args == "status" || args == "") {
      cmdOptxStatus();
    } else {
      respondError("usage: optx start <payload> | optx stop | optx status");
    }
  }
  else if (firstWord == "aotx") {
    if (args.startsWith("start ")) {
      String payload = args.substring(6);
      aotxStart(payload, 100, 1000, 2000, 1);
      respondOk();
    } else if (args == "stop") {
      aotxStop();
      respondOk();
    } else if (args == "status" || args == "") {
      cmdAotxStatus();
    } else {
      respondError("usage: aotx start <payload> | aotx stop | aotx status");
    }
  }
  else if (firstWord.length() > 0) {
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
  
  const char* cmd = req["cmd"] | "";
  const char* type = req["type"] | "";
  const char* op = req["op"] | "";
  const char* id = req["id"] | "";
  
  if (cmd[0] == '\0' && strcmp(type, "cmd") == 0 && op[0] != '\0')
    cmd = op;
  
  if (cmd[0] == '\0') {
    respondError("missing_cmd", id[0] ? id : nullptr);
    return;
  }
  
  if (strcmp(cmd, "help") == 0) { cmdHelp(id); }
  else if (strcmp(cmd, "status") == 0) { cmdStatus(id); }
  else if (strcmp(cmd, "ping") == 0) { respondOk(id); }
  else if (strcmp(cmd, "get_mac") == 0) {
    StaticJsonDocument<256> doc;
    doc["ok"] = true;
    if (id[0]) doc["id"] = id;
    doc["mac"] = getMac();
    doc["node_id"] = getNodeId();
    writeJson(doc);
  }
  else if (strcmp(cmd, "get_version") == 0) {
    StaticJsonDocument<256> doc;
    doc["ok"] = true;
    if (id[0]) doc["id"] = id;
    doc["version"] = FW_VERSION;
    doc["firmware"] = FW_NAME;
    doc["bsec2"] = true;
    writeJson(doc);
  }
  else if (strcmp(cmd, "scan") == 0 || strcmp(cmd, "i2c_scan") == 0) { cmdI2cScan(id); }
  else if (strcmp(cmd, "sensors") == 0) { cmdSensors(id); }
  else if (strcmp(cmd, "beep") == 0) {
    int freq = req["freq"] | req["frequency"] | 2000;
    int ms = req["ms"] | req["duration"] | 100;
    cmdBeep(freq, ms);
  }
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
      uint8_t r = req["r"] | 0;
      uint8_t g = req["g"] | 0;
      uint8_t b = req["b"] | 0;
      gLedR = r; gLedG = g; gLedB = b;
      gLedMode = LED_MANUAL;
      ledWriteRGB(r, g, b);
      respondOk(id);
    }
  }
  else if (strcmp(cmd, "led") == 0) {
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
  else if (strcmp(cmd, "reboot") == 0) { cmdReboot(); }
  else if (strcmp(cmd, "fmt") == 0) {
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
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  
  Serial.begin(SERIAL_BAUD);
  delay(BOOT_WAIT_MS);
  
  // Initialize sensor slot configs
  S_AMB.init("AMB", 0x77);
  S_ENV.init("ENV", 0x76);
  
  pixels.begin();
  pixels.setBrightness(50);
  pixels.clear();
  pixels.show();
  
  bootMs = millis();
  
  // Initialize LED pins (MOSFET outputs)
  for (int i = 0; i < 3; i++) pinMode(AO_PINS[i], OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  
  ledBootBlink();
  bootChime();
  
  // Initialize sensors
  initAllSensors();
  
  cmdPoster();
  
  // Boot message (JSON)
  {
    StaticJsonDocument<512> hello;
    hello["type"] = "boot";
    hello["ok"] = true;
    hello["hello"] = FW_NAME;
    hello["version"] = FW_VERSION;
    hello["node_id"] = getNodeId();
    hello["mac"] = getMac();
    hello["role"] = "side-a";
    hello["baud"] = SERIAL_BAUD;
    hello["i2c_count"] = i2cCount;
    hello["bme688_count"] = bme688_count;
    hello["bsec2"] = true;
    hello["chip"] = ESP.getChipModel();
    hello["cpu_mhz"] = ESP.getCpuFreqMHz();
    hello["heap"] = ESP.getFreeHeap();
    writeJson(hello);
  }
}

// ============================================================
// LOOP
// ============================================================
void loop() {
  yield();
  
  processSerialInput();
  
  // Run BSEC2 for each sensor
  if (S_AMB.present && S_AMB.beginOk) (void)S_AMB.bsec.run();
  if (S_ENV.present && S_ENV.beginOk) (void)S_ENV.bsec.run();
  
  ledStateUpdate();
  optxUpdate();
  aotxUpdate();
  
  if (telemetryEnabled) {
    uint32_t now = millis();
    if (now - lastTelemetryMs >= telemetryIntervalMs) {
      lastTelemetryMs = now;
      sendTelemetry();
    }
  }
}
