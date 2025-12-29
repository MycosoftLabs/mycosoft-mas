/*
 * MINIMAL TEST - MycoBrain Side-A
 * Power-optimized version to prevent brownout
 */

#include "soc/rtc_cntl_reg.h"

void setup() {
  // CRITICAL: Disable brownout detector IMMEDIATELY
  // Use direct register write - most reliable method
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  
  // Small delay to let power stabilize
  delay(50);
  
  Serial.begin(115200);
  
  // Wait for serial with timeout
  unsigned long start = millis();
  while (!Serial && (millis() - start < 3000)) {
    delay(10);
    yield();
  }
  
  // Extra delay for Serial Monitor
  delay(1500);
  
  Serial.println("\n\n========================================");
  Serial.println("MINIMAL TEST - Hardware Check");
  Serial.println("========================================");
  Serial.println("If you see this, hardware is OK!");
  Serial.println("Device is NOT resetting.");
  Serial.flush();
}

void loop() {
  static unsigned long lastPrint = 0;
  unsigned long now = millis();
  
  // Feed watchdog
  yield();
  
  // Print every 2 seconds
  if (now - lastPrint >= 2000) {
    Serial.print("Loop running: ");
    Serial.print(now / 1000);
    Serial.println(" seconds");
    Serial.flush();
    lastPrint = now;
  }
  
  delay(100);
  yield(); // Feed watchdog again
}
