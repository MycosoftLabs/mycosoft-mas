#include <Arduino.h>
#include <ArduinoJson.h>
#include <Wire.h>

// Pin definitions
#define PIN_SDA 5
#define PIN_SCL 4
#define PIN_LED_R 12
#define PIN_LED_G 13
#define PIN_LED_B 14
#define PIN_BUZZER 16
#define PIN_NEOPIXEL 15

static uint32_t bootTime = 0;
static uint32_t telemetrySeq = 0;

void sendJson(JsonDocument& doc) {
    serializeJson(doc, Serial);
    Serial.println();
}

void sendHello() {
    StaticJsonDocument<256> doc;
    doc["ok"] = true;
    doc["hello"] = "mycobrain-working";
    doc["version"] = "1.0.0";
    doc["node_id"] = String((uint32_t)(ESP.getEfuseMac() >> 24), HEX);
    doc["role"] = "side-a";
    doc["baud"] = 115200;
    doc["heap"] = ESP.getFreeHeap();
    doc["psram"] = ESP.getPsramSize();
    sendJson(doc);
}

void scanI2C() {
    StaticJsonDocument<512> doc;
    doc["type"] = "i2c_scan";
    JsonArray devices = doc.createNestedArray("devices");
    
    Wire.begin(PIN_SDA, PIN_SCL);
    Wire.setClock(100000);
    
    for (uint8_t addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            devices.add(addr);
        }
    }
    sendJson(doc);
}

void sendTelemetry() {
    StaticJsonDocument<512> doc;
    doc["type"] = "telemetry";
    doc["seq"] = telemetrySeq++;
    doc["uptime_ms"] = millis() - bootTime;
    doc["heap"] = ESP.getFreeHeap();
    sendJson(doc);
}

void handleCommand(const String& cmd) {
    if (cmd == "status" || cmd == "hello") {
        sendHello();
    } else if (cmd == "scan" || cmd == "i2c") {
        scanI2C();
    } else if (cmd.startsWith("led ")) {
        // Simple LED control
        String color = cmd.substring(4);
        if (color == "red") {
            digitalWrite(PIN_LED_R, HIGH);
            digitalWrite(PIN_LED_G, LOW);
            digitalWrite(PIN_LED_B, LOW);
        } else if (color == "green") {
            digitalWrite(PIN_LED_R, LOW);
            digitalWrite(PIN_LED_G, HIGH);
            digitalWrite(PIN_LED_B, LOW);
        } else if (color == "blue") {
            digitalWrite(PIN_LED_R, LOW);
            digitalWrite(PIN_LED_G, LOW);
            digitalWrite(PIN_LED_B, HIGH);
        } else if (color == "off") {
            digitalWrite(PIN_LED_R, LOW);
            digitalWrite(PIN_LED_G, LOW);
            digitalWrite(PIN_LED_B, LOW);
        }
        StaticJsonDocument<64> doc;
        doc["ok"] = true;
        doc["led"] = color;
        sendJson(doc);
    } else if (cmd.startsWith("buzzer ")) {
        String pattern = cmd.substring(7);
        if (pattern == "coin") {
            tone(PIN_BUZZER, 988, 100);
            delay(100);
            tone(PIN_BUZZER, 1319, 300);
        } else if (pattern == "beep") {
            tone(PIN_BUZZER, 1000, 100);
        }
        StaticJsonDocument<64> doc;
        doc["ok"] = true;
        doc["buzzer"] = pattern;
        sendJson(doc);
    } else {
        StaticJsonDocument<64> doc;
        doc["error"] = "unknown command";
        doc["cmd"] = cmd;
        sendJson(doc);
    }
}

void setup() {
    Serial.begin(115200);
    delay(2000);
    
    bootTime = millis();
    
    // Setup pins
    pinMode(PIN_LED_R, OUTPUT);
    pinMode(PIN_LED_G, OUTPUT);
    pinMode(PIN_LED_B, OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);
    pinMode(PIN_NEOPIXEL, OUTPUT);
    
    // Boot LED flash
    digitalWrite(PIN_LED_G, HIGH);
    delay(100);
    digitalWrite(PIN_LED_G, LOW);
    
    // Boot beep
    tone(PIN_BUZZER, 523, 50);
    delay(60);
    tone(PIN_BUZZER, 659, 50);
    delay(60);
    tone(PIN_BUZZER, 784, 80);
    delay(100);
    noTone(PIN_BUZZER);
    
    sendHello();
}

void loop() {
    static uint32_t lastTelemetry = 0;
    
    // Handle serial commands
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        if (cmd.length() > 0) {
            handleCommand(cmd);
        }
    }
    
    // Send telemetry every 5 seconds
    if (millis() - lastTelemetry >= 5000) {
        lastTelemetry = millis();
        sendTelemetry();
    }
}