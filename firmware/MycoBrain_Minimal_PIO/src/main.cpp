#include <Arduino.h>

#define BUZZER 16

String inputBuffer = "";

void setup() {
    Serial.begin(115200);
    delay(3000);  // Long delay for USB stabilization
    
    pinMode(BUZZER, OUTPUT);
    
    // Boot beep
    tone(BUZZER, 800, 100);
    delay(150);
    noTone(BUZZER);
    
    Serial.println("{\"ok\":true,\"hello\":\"mycobrain\",\"version\":\"minimal-test\"}");
}

void loop() {
    while (Serial.available()) {
        char c = Serial.read();
        if (c == '\n' || c == '\r') {
            if (inputBuffer.length() > 0) {
                inputBuffer.trim();
                if (inputBuffer == "beep") {
                    tone(BUZZER, 1000, 100);
                    delay(150);
                    noTone(BUZZER);
                    Serial.println("{\"ok\":true,\"buzzer\":\"beep\"}");
                } else if (inputBuffer == "coin") {
                    tone(BUZZER, 988, 100);
                    delay(100);
                    tone(BUZZER, 1319, 300);
                    delay(350);
                    noTone(BUZZER);
                    Serial.println("{\"ok\":true,\"buzzer\":\"coin\"}");
                } else if (inputBuffer == "status") {
                    Serial.print("{\"ok\":true,\"heap\":");
                    Serial.print(ESP.getFreeHeap());
                    Serial.println("}");
                } else {
                    Serial.println("{\"ok\":true,\"echo\":\"" + inputBuffer + "\"}");
                }
                inputBuffer = "";
            }
        } else {
            inputBuffer += c;
        }
    }
    delay(10);
}