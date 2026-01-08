#include <Arduino.h>
#include <Wire.h>

#define PIN_SDA 5
#define PIN_SCL 4
#define LED_R 12
#define LED_G 13
#define LED_B 14
#define BUZZER 16

static uint32_t bootTime = 0;
static uint32_t telemetrySeq = 0;
static uint8_t i2cDevices[16];
static uint8_t i2cCount = 0;

void scanI2C() {
    i2cCount = 0;
    for (uint8_t addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0 && i2cCount < 16) {
            i2cDevices[i2cCount++] = addr;
        }
    }
}

void sendHello() {
    Serial.print("{\"ok\":true,\"hello\":\"mycobrain\",\"version\":\"1.2.0\",");
    Serial.print("\"firmware\":\"dualmode-pio\",");
    Serial.print("\"heap\":");
    Serial.print(ESP.getFreeHeap());
    Serial.println("}");
}

void sendStatus() {
    Serial.print("{\"type\":\"status\",\"uptime_ms\":");
    Serial.print(millis() - bootTime);
    Serial.print(",\"heap\":");
    Serial.print(ESP.getFreeHeap());
    Serial.print(",\"i2c_devices\":[");
    for (int i = 0; i < i2cCount; i++) {
        if (i > 0) Serial.print(",");
        Serial.print(i2cDevices[i]);
    }
    Serial.println("]}");
}

void sendTelemetry() {
    Serial.print("{\"type\":\"telemetry\",\"seq\":");
    Serial.print(telemetrySeq++);
    Serial.print(",\"uptime_ms\":");
    Serial.print(millis() - bootTime);
    Serial.print(",\"heap\":");
    Serial.print(ESP.getFreeHeap());
    Serial.println("}");
}

void handleCommand(String cmd) {
    cmd.trim();
    if (cmd == "status" || cmd == "hello") {
        sendStatus();
    } else if (cmd == "scan") {
        scanI2C();
        sendStatus();
    } else if (cmd.startsWith("led ")) {
        String color = cmd.substring(4);
        if (color == "red") { analogWrite(LED_R, 255); analogWrite(LED_G, 0); analogWrite(LED_B, 0); }
        else if (color == "green") { analogWrite(LED_R, 0); analogWrite(LED_G, 255); analogWrite(LED_B, 0); }
        else if (color == "blue") { analogWrite(LED_R, 0); analogWrite(LED_G, 0); analogWrite(LED_B, 255); }
        else if (color == "off") { analogWrite(LED_R, 0); analogWrite(LED_G, 0); analogWrite(LED_B, 0); }
        Serial.print("{\"ok\":true,\"led\":\"");
        Serial.print(color);
        Serial.println("\"}");
    } else if (cmd.startsWith("buzzer ")) {
        String pattern = cmd.substring(7);
        if (pattern == "coin") {
            tone(BUZZER, 988, 100);
            delay(100);
            tone(BUZZER, 1319, 300);
            delay(350);
            noTone(BUZZER);
        } else if (pattern == "beep") {
            tone(BUZZER, 1000, 100);
            delay(150);
            noTone(BUZZER);
        }
        Serial.print("{\"ok\":true,\"buzzer\":\"");
        Serial.print(pattern);
        Serial.println("\"}");
    }
}

void setup() {
    Serial.begin(115200);
    delay(2000);
    
    bootTime = millis();
    
    Wire.begin(PIN_SDA, PIN_SCL);
    Wire.setClock(100000);
    
    pinMode(LED_R, OUTPUT);
    pinMode(LED_G, OUTPUT);
    pinMode(LED_B, OUTPUT);
    pinMode(BUZZER, OUTPUT);
    
    // Boot sequence - LED flash
    analogWrite(LED_G, 255);
    delay(100);
    analogWrite(LED_G, 0);
    
    // Boot jingle
    tone(BUZZER, 523, 50);
    delay(60);
    tone(BUZZER, 659, 50);
    delay(60);
    tone(BUZZER, 784, 80);
    delay(100);
    noTone(BUZZER);
    
    // Initial I2C scan
    scanI2C();
    
    sendHello();
}

void loop() {
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        handleCommand(cmd);
    }
    
    static uint32_t lastTelemetry = 0;
    if (millis() - lastTelemetry >= 5000) {
        lastTelemetry = millis();
        sendTelemetry();
    }
}