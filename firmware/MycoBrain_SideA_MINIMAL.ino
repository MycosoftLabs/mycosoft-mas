/*
 * MycoBrain Side-A MINIMAL TEST
 * Use this to test if hardware is OK
 * If this works, the issue is in sensor/BSEC code
 */

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("\n\n=== MINIMAL TEST ===");
  Serial.println("If you see this repeatedly, hardware is OK");
  Serial.println("If it stops, there's a hardware issue");
}

void loop() {
  static unsigned long lastPrint = 0;
  unsigned long now = millis();
  
  if (now - lastPrint >= 1000) {
    Serial.print("Loop running: ");
    Serial.print(now / 1000);
    Serial.println(" seconds");
    lastPrint = now;
  }
  
  delay(100);
}

