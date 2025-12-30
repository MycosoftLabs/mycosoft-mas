// Simple LED test for MycoBrain Side-A
// LED pins: R=12, G=13, B=14

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("LED TEST STARTING");
  
  // Configure pins as outputs
  pinMode(12, OUTPUT);
  pinMode(13, OUTPUT);
  pinMode(14, OUTPUT);
  
  // Also try pins 16 (buzzer) to confirm it works
  pinMode(16, OUTPUT);
  
  Serial.println("Pins configured");
}

void loop() {
  Serial.println("RED ON");
  digitalWrite(12, HIGH);
  digitalWrite(13, LOW);
  digitalWrite(14, LOW);
  tone(16, 1000, 100);
  delay(1000);
  
  Serial.println("GREEN ON");
  digitalWrite(12, LOW);
  digitalWrite(13, HIGH);
  digitalWrite(14, LOW);
  tone(16, 1500, 100);
  delay(1000);
  
  Serial.println("BLUE ON");
  digitalWrite(12, LOW);
  digitalWrite(13, LOW);
  digitalWrite(14, HIGH);
  tone(16, 2000, 100);
  delay(1000);
  
  Serial.println("ALL ON (WHITE)");
  digitalWrite(12, HIGH);
  digitalWrite(13, HIGH);
  digitalWrite(14, HIGH);
  delay(1000);
  
  Serial.println("ALL OFF");
  digitalWrite(12, LOW);
  digitalWrite(13, LOW);
  digitalWrite(14, LOW);
  delay(1000);
}

