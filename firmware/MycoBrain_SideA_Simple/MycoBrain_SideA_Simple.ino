/*
 * MycoBrain Side-A — Simple Test Firmware (No ArduinoJson)
 * 
 * Minimal firmware to test if the board is stable
 * Uses only core Arduino functions
 */

#include <Arduino.h>
#include <Wire.h>

// Brownout disable
#include "soc/rtc_cntl_reg.h"

// Pins from ESP32AB workbook
static const uint8_t PIN_SDA = 5;
static const uint8_t PIN_SCL = 4;
static const uint8_t AO_PINS[3] = {12, 13, 14};  // R, G, B
static const uint8_t BUZZER_PIN = 16;

static uint32_t bootMs = 0;
static uint32_t seq = 0;

void setup() {
  // Disable brownout FIRST
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  
  // Initialize serial
  Serial.begin(115200);
  
  // Boot wait (like Garrett's code)
  delay(1800);
  
  bootMs = millis();
  
  // Initialize I2C
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(100000);
  
  // Initialize LED pins
  pinMode(AO_PINS[0], OUTPUT);
  pinMode(AO_PINS[1], OUTPUT);
  pinMode(AO_PINS[2], OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  
  // Boot LED sequence
  for (int i = 0; i < 3; i++) {
    analogWrite(AO_PINS[2], 60);  // Blue
    delay(60);
    analogWrite(AO_PINS[2], 0);
    analogWrite(AO_PINS[1], 60);  // Green
    delay(60);
    analogWrite(AO_PINS[1], 0);
    analogWrite(AO_PINS[0], 60);  // Red
    delay(60);
    analogWrite(AO_PINS[0], 0);
    delay(40);
  }
  
  // Boot chime
  tone(BUZZER_PIN, 523, 60);
  delay(70);
  tone(BUZZER_PIN, 659, 60);
  delay(70);
  tone(BUZZER_PIN, 784, 80);
  delay(90);
  noTone(BUZZER_PIN);
  
  // Get MAC
  uint64_t efuse = ESP.getEfuseMac();
  char mac[18];
  snprintf(mac, sizeof(mac), "%02X:%02X:%02X:%02X:%02X:%02X",
    (uint8_t)(efuse >> 40), (uint8_t)(efuse >> 32),
    (uint8_t)(efuse >> 24), (uint8_t)(efuse >> 16),
    (uint8_t)(efuse >> 8), (uint8_t)(efuse));
  
  // Print boot message
  Serial.println();
  Serial.println("====================================");
  Serial.println("  MycoBrain Side-A Simple Test");
  Serial.println("====================================");
  Serial.print("MAC: ");
  Serial.println(mac);
  Serial.print("Chip: ");
  Serial.println(ESP.getChipModel());
  Serial.print("CPU: ");
  Serial.print(ESP.getCpuFreqMHz());
  Serial.println(" MHz");
  Serial.print("Heap: ");
  Serial.println(ESP.getFreeHeap());
  
  // I2C scan
  Serial.println("\nI2C Scan:");
  int count = 0;
  for (uint8_t addr = 0x08; addr < 0x78; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("  Found: 0x");
      Serial.println(addr, HEX);
      count++;
    }
  }
  if (count == 0) Serial.println("  (none found)");
  
  Serial.println("\nReady! Type 'help' for commands.");
  Serial.println("====================================\n");
}

void loop() {
  // LED heartbeat (green pulse)
  uint8_t v = (uint8_t)(40 + 20 * sin((double)millis() / 800.0));
  analogWrite(AO_PINS[1], v);
  
  // Handle serial input
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    line.toLowerCase();
    
    if (line == "help" || line == "?") {
      Serial.println("Commands: help, status, ping, scan, beep, reboot");
    }
    else if (line == "status") {
      uint32_t uptime = (millis() - bootMs) / 1000;
      Serial.print("uptime=");
      Serial.print(uptime);
      Serial.print("s heap=");
      Serial.print(ESP.getFreeHeap());
      Serial.print(" seq=");
      Serial.println(seq);
    }
    else if (line == "ping") {
      Serial.println("pong");
    }
    else if (line == "scan" || line == "i2c") {
      Serial.println("I2C Scan:");
      int count = 0;
      for (uint8_t addr = 0x08; addr < 0x78; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
          Serial.print("  0x");
          Serial.println(addr, HEX);
          count++;
        }
      }
      Serial.print("count=");
      Serial.println(count);
    }
    else if (line == "beep") {
      tone(BUZZER_PIN, 2000, 100);
      Serial.println("ok");
    }
    else if (line == "reboot") {
      Serial.println("rebooting...");
      delay(100);
      ESP.restart();
    }
    else if (line.length() > 0) {
      Serial.println("unknown command");
    }
  }
  
  // Periodic telemetry (every 5 seconds)
  static uint32_t lastTelemetry = 0;
  if (millis() - lastTelemetry >= 5000) {
    lastTelemetry = millis();
    uint32_t uptime = (millis() - bootMs) / 1000;
    
    // Simple JSON-like output for website
    Serial.print("{\"type\":\"tele\",\"seq\":");
    Serial.print(seq++);
    Serial.print(",\"uptime_s\":");
    Serial.print(uptime);
    Serial.print(",\"heap\":");
    Serial.print(ESP.getFreeHeap());
    Serial.println("}");
  }
  
  delay(10);
}

