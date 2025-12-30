/*
 * MycoBrain Minimal Blink - Power Test Firmware
 * 
 * Absolute minimum code to test if the board can boot.
 * Uses only the built-in LED pins with no external dependencies.
 * 
 * If this works, the board hardware is OK.
 * If this fails, there's a hardware power issue.
 */

#include "soc/rtc_cntl_reg.h"

// LED pins from schematic (PWM RGB)
#define LED_R 12
#define LED_G 13
#define LED_B 14

void setup() {
  // IMMEDIATELY disable brownout detector
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  
  // Small delay for power to stabilize
  delay(100);
  
  // Setup LED pins
  pinMode(LED_R, OUTPUT);
  pinMode(LED_G, OUTPUT);
  pinMode(LED_B, OUTPUT);
  
  // Turn on green LED immediately
  digitalWrite(LED_G, HIGH);
  
  // Start serial
  Serial.begin(115200);
  delay(1000);
  
  Serial.println();
  Serial.println("=================================");
  Serial.println("MycoBrain Minimal Blink - WORKING");
  Serial.println("=================================");
  Serial.println("If you see this, the board boots!");
  Serial.println();
}

void loop() {
  // Blink pattern: Green -> Blue -> Red -> Off
  
  // Green
  digitalWrite(LED_R, LOW);
  digitalWrite(LED_G, HIGH);
  digitalWrite(LED_B, LOW);
  Serial.println("LED: GREEN");
  delay(500);
  
  // Blue
  digitalWrite(LED_R, LOW);
  digitalWrite(LED_G, LOW);
  digitalWrite(LED_B, HIGH);
  Serial.println("LED: BLUE");
  delay(500);
  
  // Red
  digitalWrite(LED_R, HIGH);
  digitalWrite(LED_G, LOW);
  digitalWrite(LED_B, LOW);
  Serial.println("LED: RED");
  delay(500);
  
  // All off
  digitalWrite(LED_R, LOW);
  digitalWrite(LED_G, LOW);
  digitalWrite(LED_B, LOW);
  Serial.println("LED: OFF");
  delay(500);
}

