#include <Arduino.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_BME680.h>
#include "mdp_codec.h"

// Side A hardware pins (ESP32-S3)
static const int I2C_SDA = 5;
static const int I2C_SCL = 4;
static const int AI_PINS[4] = {6, 7, 10, 11};
static const int MOSFET_PINS[3] = {12, 13, 14};
static const int NEOPIXEL_PIN = 15;
static const int BUZZER_PIN = 16;

static const uint8_t BME_ADDRS[2] = {0x76, 0x77};
static const char* FW_VERSION = "side-a-mdp-1.0.0";

Adafruit_BME680 bme1;
Adafruit_BME680 bme2;
bool bme1_ok = false;
bool bme2_ok = false;
bool estop_active = false;

uint32_t tx_seq = 1;
uint32_t last_stream_ms = 0;
uint32_t stream_interval_ms = 10000;

uint8_t cobs_buffer[1024];
size_t cobs_len = 0;

void send_frame(uint8_t msg_type, uint32_t ack, uint8_t flags, const JsonDocument& payload) {
  uint8_t raw[1024];
  uint8_t encoded[1100];

  MdpHeader hdr{};
  hdr.magic = MDP_MAGIC;
  hdr.version = MDP_VERSION;
  hdr.msg_type = msg_type;
  hdr.seq = tx_seq++;
  hdr.ack = ack;
  hdr.flags = flags;
  hdr.src = EP_SIDE_A;
  hdr.dst = EP_GATEWAY;
  hdr.rsv = 0;

  memcpy(raw, &hdr, sizeof(MdpHeader));
  size_t payload_len = serializeJson(payload, raw + sizeof(MdpHeader), sizeof(raw) - sizeof(MdpHeader) - 2);
  size_t frame_len = sizeof(MdpHeader) + payload_len;

  uint16_t crc = mdp_crc16_ccitt_false(raw, frame_len);
  raw[frame_len] = static_cast<uint8_t>(crc & 0xFF);
  raw[frame_len + 1] = static_cast<uint8_t>((crc >> 8) & 0xFF);
  frame_len += 2;

  size_t enc_len = mdp_cobs_encode(raw, frame_len, encoded, sizeof(encoded));
  if (enc_len == 0) return;

  Serial.write(encoded, enc_len);
  Serial.write('\0');
  Serial.flush();
}

bool parse_frame(const uint8_t* encoded, size_t len, MdpHeader& hdr, DynamicJsonDocument& payload) {
  uint8_t decoded[1024];
  size_t dec_len = mdp_cobs_decode(encoded, len, decoded, sizeof(decoded));
  if (dec_len < sizeof(MdpHeader) + 2) return false;

  memcpy(&hdr, decoded, sizeof(MdpHeader));
  if (hdr.magic != MDP_MAGIC || hdr.version != MDP_VERSION) return false;

  uint16_t got_crc = static_cast<uint16_t>(decoded[dec_len - 2]) | (static_cast<uint16_t>(decoded[dec_len - 1]) << 8);
  uint16_t expected_crc = mdp_crc16_ccitt_false(decoded, dec_len - 2);
  if (got_crc != expected_crc) return false;

  size_t payload_len = dec_len - sizeof(MdpHeader) - 2;
  auto err = deserializeJson(payload, decoded + sizeof(MdpHeader), payload_len);
  return !err;
}

void send_ack(uint32_t ack_seq, bool success, const char* message) {
  StaticJsonDocument<192> doc;
  doc["success"] = success;
  doc["message"] = message;
  send_frame(MDP_ACK, ack_seq, success ? IS_ACK : IS_NACK, doc);
}

void send_hello(uint32_t ack_seq = 0) {
  StaticJsonDocument<384> doc;
  doc["device_id"] = String("mycobrain-") + String((uint32_t)(ESP.getEfuseMac() & 0xFFFFFF), HEX);
  doc["firmware_version"] = FW_VERSION;
  doc["role"] = "side_a";
  JsonArray sensors = doc.createNestedArray("sensors");
  sensors.add("bme688_a");
  sensors.add("bme688_b");
  sensors.add("ai1");
  sensors.add("ai2");
  sensors.add("ai3");
  sensors.add("ai4");
  JsonArray capabilities = doc.createNestedArray("capabilities");
  capabilities.add("i2c");
  capabilities.add("telemetry");
  capabilities.add("led");
  capabilities.add("buzzer");
  capabilities.add("output_control");
  capabilities.add("estop");
  send_frame(MDP_HELLO, ack_seq, 0, doc);
}

void set_outputs_safe() {
  for (int i = 0; i < 3; ++i) digitalWrite(MOSFET_PINS[i], LOW);
  digitalWrite(NEOPIXEL_PIN, LOW);
  noTone(BUZZER_PIN);
}

void send_telemetry(uint32_t ack_seq = 0) {
  StaticJsonDocument<512> doc;
  doc["type"] = "telemetry";
  doc["uptime_s"] = millis() / 1000;
  doc["estop"] = estop_active;

  JsonObject ai = doc.createNestedObject("analog");
  ai["ai1"] = analogRead(AI_PINS[0]);
  ai["ai2"] = analogRead(AI_PINS[1]);
  ai["ai3"] = analogRead(AI_PINS[2]);
  ai["ai4"] = analogRead(AI_PINS[3]);

  JsonObject bme = doc.createNestedObject("bme688");
  if (bme1_ok && bme1.performReading()) {
    JsonObject b1 = bme.createNestedObject("a");
    b1["temperature_c"] = bme1.temperature;
    b1["humidity_pct"] = bme1.humidity;
    b1["pressure_hpa"] = bme1.pressure / 100.0;
    b1["gas_ohm"] = bme1.gas_resistance;
  }
  if (bme2_ok && bme2.performReading()) {
    JsonObject b2 = bme.createNestedObject("b");
    b2["temperature_c"] = bme2.temperature;
    b2["humidity_pct"] = bme2.humidity;
    b2["pressure_hpa"] = bme2.pressure / 100.0;
    b2["gas_ohm"] = bme2.gas_resistance;
  }

  send_frame(MDP_TELEMETRY, ack_seq, 0, doc);
}

void handle_command(const MdpHeader& hdr, DynamicJsonDocument& payload) {
  const char* cmd = payload["cmd"] | "";
  JsonVariant params = payload["params"];

  if (strcmp(cmd, "hello") == 0) {
    send_hello(hdr.seq);
    return;
  }
  if (strcmp(cmd, "health") == 0 || strcmp(cmd, "read_sensors") == 0) {
    send_telemetry(hdr.seq);
    if (hdr.flags & ACK_REQUESTED) send_ack(hdr.seq, true, "telemetry_sent");
    return;
  }
  if (strcmp(cmd, "stream_sensors") == 0) {
    float rate_hz = params["rate_hz"] | 0.1f;
    if (rate_hz < 0.1f) rate_hz = 0.1f;
    stream_interval_ms = (uint32_t)(1000.0f / rate_hz);
    send_ack(hdr.seq, true, "stream_interval_updated");
    return;
  }
  if (strcmp(cmd, "output_control") == 0) {
    if (estop_active) {
      send_ack(hdr.seq, false, "estop_active");
      return;
    }
    const char* id = params["id"] | "";
    int value = params["value"] | 0;
    if (strncmp(id, "mosfet", 6) == 0) {
      int idx = atoi(id + 6) - 1;
      if (idx >= 0 && idx < 3) {
        digitalWrite(MOSFET_PINS[idx], value ? HIGH : LOW);
        send_ack(hdr.seq, true, "mosfet_updated");
        return;
      }
    } else if (strcmp(id, "buzzer") == 0) {
      int freq = params["freq"] | 1200;
      int dur_ms = params["duration_ms"] | 200;
      tone(BUZZER_PIN, freq, dur_ms);
      send_ack(hdr.seq, true, "buzzer_played");
      return;
    } else if (strcmp(id, "neopixel") == 0) {
      digitalWrite(NEOPIXEL_PIN, value ? HIGH : LOW);
      send_ack(hdr.seq, true, "neopixel_updated");
      return;
    }
    send_ack(hdr.seq, false, "invalid_output_id");
    return;
  }
  if (strcmp(cmd, "estop") == 0) {
    estop_active = true;
    set_outputs_safe();
    StaticJsonDocument<128> evt;
    evt["event"] = "estop_activated";
    send_frame(MDP_EVENT, hdr.seq, 0, evt);
    send_ack(hdr.seq, true, "estop_activated");
    return;
  }
  if (strcmp(cmd, "clear_estop") == 0) {
    estop_active = false;
    send_ack(hdr.seq, true, "estop_cleared");
    return;
  }
  if (strcmp(cmd, "enable_peripheral") == 0 || strcmp(cmd, "disable_peripheral") == 0) {
    // Side A acknowledges peripheral intent; real low-level toggling is hardware-specific.
    send_ack(hdr.seq, true, "peripheral_state_recorded");
    return;
  }

  send_ack(hdr.seq, false, "unknown_command");
}

void setup() {
  Serial.begin(115200);
  delay(1200);
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(100000);

  for (int i = 0; i < 3; ++i) {
    pinMode(MOSFET_PINS[i], OUTPUT);
    digitalWrite(MOSFET_PINS[i], LOW);
  }
  pinMode(NEOPIXEL_PIN, OUTPUT);
  digitalWrite(NEOPIXEL_PIN, LOW);
  pinMode(BUZZER_PIN, OUTPUT);
  noTone(BUZZER_PIN);

  bme1_ok = bme1.begin(BME_ADDRS[0], &Wire);
  bme2_ok = bme2.begin(BME_ADDRS[1], &Wire);
  send_hello();
}

void loop() {
  while (Serial.available() > 0) {
    uint8_t b = (uint8_t)Serial.read();
    if (b == 0x00) {
      if (cobs_len > 0) {
        MdpHeader hdr{};
        DynamicJsonDocument payload(512);
        if (parse_frame(cobs_buffer, cobs_len, hdr, payload) && hdr.msg_type == MDP_COMMAND && hdr.dst == EP_SIDE_A) {
          handle_command(hdr, payload);
        }
      }
      cobs_len = 0;
    } else if (cobs_len < sizeof(cobs_buffer)) {
      cobs_buffer[cobs_len++] = b;
    } else {
      cobs_len = 0;
    }
  }

  if (millis() - last_stream_ms >= stream_interval_ms) {
    send_telemetry();
    last_stream_ms = millis();
  }
  delay(5);
}
