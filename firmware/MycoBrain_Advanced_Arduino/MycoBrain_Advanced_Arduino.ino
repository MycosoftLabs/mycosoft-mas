/**
 * MycoBrain Advanced Firmware v2.0 - Arduino IDE Version
 * 
 * ESP32-S3 based environmental sensing and science communication platform.
 * This is a consolidated single-file version for Arduino IDE.
 * 
 * REQUIRED LIBRARIES (install via Library Manager):
 * - NeoPixelBus by Makuna (v2.7.9+)
 * - ArduinoJson by Benoit Blanchon (v7.0.0+)
 * 
 * BOARD SETTINGS:
 * - Board: ESP32-S3 Dev Module
 * - CPU Frequency: 240 MHz
 * - Flash Mode: QIO @ 80 MHz
 * - Flash Size: 16 MB
 * - Partition Scheme: 16MB Flash (3MB App / 9.9MB FATFS)
 * - PSRAM: OPI PSRAM
 * - USB CDC On Boot: Enabled
 * - USB Mode: Hardware CDC and JTAG
 * 
 * @author Mycosoft
 * @version 2.0.0
 */

#include <Arduino.h>
#include <NeoPixelBus.h>
#include <ArduinoJson.h>
#include <Wire.h>

// =============================================================================
// CONFIGURATION
// =============================================================================

#define FIRMWARE_NAME       "MycoBrain-Advanced"
#define FIRMWARE_VERSION    "2.0.0"

// Hardware Pins - VERIFIED FROM SCHEMATIC
#define PIN_NEOPIXEL        15    // SK6805 NeoPixel data
#define PIN_BUZZER          16    // MOSFET-driven buzzer
#define PIN_I2C_SCL         4     // I2C Clock
#define PIN_I2C_SDA         5     // I2C Data
#define PIN_OUT_1           12    // MOSFET output 1
#define PIN_OUT_2           13    // MOSFET output 2
#define PIN_OUT_3           14    // MOSFET output 3

// Serial
#define SERIAL_BAUD         115200
#define CLI_BUFFER_SIZE     512

// =============================================================================
// OPERATING MODE
// =============================================================================
enum class OpMode { HUMAN, MACHINE };
static OpMode currentMode = OpMode::HUMAN;
static bool debugEnabled = false;

// =============================================================================
// NEOPIXEL (NeoPixelBus)
// =============================================================================
static NeoPixelBus<NeoGrbFeature, NeoEsp32Rmt0Ws2812xMethod> strip(1, PIN_NEOPIXEL);
static uint8_t ledR = 0, ledG = 0, ledB = 0;
static bool ledOn = false;

void ledSetRGB(uint8_t r, uint8_t g, uint8_t b) {
    ledR = r; ledG = g; ledB = b;
    ledOn = (r > 0 || g > 0 || b > 0);
    strip.SetPixelColor(0, RgbColor(r, g, b));
    strip.Show();
}

void ledOff() {
    ledSetRGB(0, 0, 0);
    ledOn = false;
}

// =============================================================================
// BUZZER (LEDC PWM)
// =============================================================================
#define BUZZER_CHANNEL  0

void buzzerTone(uint16_t freq, uint16_t duration_ms = 0) {
    if (freq == 0) {
        ledcWrite(BUZZER_CHANNEL, 0);
    } else {
        ledcWriteTone(BUZZER_CHANNEL, freq);
        ledcWrite(BUZZER_CHANNEL, 127);
    }
    if (duration_ms > 0) {
        delay(duration_ms);
        ledcWrite(BUZZER_CHANNEL, 0);
    }
}

void buzzerStop() {
    ledcWrite(BUZZER_CHANNEL, 0);
}

// Pattern definitions
struct BuzzNote { uint16_t freq; uint16_t dur; };

static const BuzzNote coinNotes[] = {{988, 100}, {1319, 300}};
static const BuzzNote bumpNotes[] = {{200, 50}, {150, 50}};
static const BuzzNote powerNotes[] = {{523, 50}, {659, 50}, {784, 50}, {1047, 50}, {1319, 50}, {1568, 50}, {2093, 150}};
static const BuzzNote oneUpNotes[] = {{1319, 100}, {1568, 100}, {2637, 100}, {2093, 100}, {2349, 100}, {3136, 200}};
static const BuzzNote morgioNotes[] = {
    {659, 150}, {0, 50}, {784, 150}, {0, 50}, {880, 150}, {0, 50},
    {784, 150}, {0, 50}, {659, 300}, {0, 100}, {523, 150}, {0, 50},
    {587, 150}, {0, 50}, {659, 400}
};
static const BuzzNote alertNotes[] = {{2000, 100}, {0, 100}, {2000, 100}, {0, 100}, {2000, 100}};
static const BuzzNote successNotes[] = {{523, 100}, {659, 100}, {784, 200}};
static const BuzzNote errorNotes[] = {{200, 150}, {0, 50}, {200, 150}};

void playPattern(const BuzzNote* notes, size_t count) {
    for (size_t i = 0; i < count; i++) {
        buzzerTone(notes[i].freq, notes[i].dur);
    }
}

void buzzerPattern(const char* name) {
    if (strcmp(name, "coin") == 0) playPattern(coinNotes, 2);
    else if (strcmp(name, "bump") == 0) playPattern(bumpNotes, 2);
    else if (strcmp(name, "power") == 0) playPattern(powerNotes, 7);
    else if (strcmp(name, "1up") == 0) playPattern(oneUpNotes, 6);
    else if (strcmp(name, "morgio") == 0) playPattern(morgioNotes, 15);
    else if (strcmp(name, "alert") == 0) playPattern(alertNotes, 5);
    else if (strcmp(name, "success") == 0) playPattern(successNotes, 3);
    else if (strcmp(name, "error") == 0) playPattern(errorNotes, 3);
}

// =============================================================================
// JSON OUTPUT HELPERS
// =============================================================================

void emitAck(const char* cmd, const char* msg = nullptr) {
    StaticJsonDocument<256> doc;
    doc["type"] = "ack";
    doc["cmd"] = cmd;
    if (msg) doc["msg"] = msg;
    doc["ok"] = true;
    serializeJson(doc, Serial);
    Serial.println();
}

void emitError(const char* cmd, const char* error) {
    StaticJsonDocument<256> doc;
    doc["type"] = "err";
    doc["cmd"] = cmd;
    doc["error"] = error;
    doc["ok"] = false;
    serializeJson(doc, Serial);
    Serial.println();
}

void emitStatus() {
    StaticJsonDocument<1024> doc;
    doc["type"] = "status";
    doc["firmware"] = FIRMWARE_NAME;
    doc["version"] = FIRMWARE_VERSION;
    doc["uptime_ms"] = millis();
    doc["mode"] = (currentMode == OpMode::MACHINE) ? "machine" : "human";
    doc["led"]["r"] = ledR;
    doc["led"]["g"] = ledG;
    doc["led"]["b"] = ledB;
    doc["led"]["on"] = ledOn;
    serializeJson(doc, Serial);
    Serial.println();
}

// =============================================================================
// PERIPHERAL DISCOVERY
// =============================================================================

void scanI2C() {
    StaticJsonDocument<1024> doc;
    doc["type"] = "periph_list";
    JsonArray list = doc["devices"].to<JsonArray>();
    
    for (uint8_t addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            JsonObject dev = list.add<JsonObject>();
            dev["address"] = addr;
            char addrStr[8];
            snprintf(addrStr, sizeof(addrStr), "0x%02X", addr);
            dev["hex"] = addrStr;
            
            // Identify known devices
            if (addr == 0x76 || addr == 0x77) dev["type"] = "BME688";
            else if (addr == 0x44 || addr == 0x45) dev["type"] = "SHT4x";
            else if (addr == 0x3C || addr == 0x3D) dev["type"] = "OLED";
            else if (addr == 0x29) dev["type"] = "VL53L0X";
            else dev["type"] = "unknown";
        }
    }
    
    doc["count"] = list.size();
    serializeJson(doc, Serial);
    Serial.println();
}

// =============================================================================
// OPTICAL MODEM
// =============================================================================

static bool optxActive = false;
static uint8_t* optxPayload = nullptr;
static size_t optxLen = 0;
static size_t optxByteIdx = 0;
static uint8_t optxBitIdx = 0;
static uint32_t optxLastSymbol = 0;
static uint16_t optxPeriod = 100;
static bool optxRepeat = false;
static uint8_t optxR = 255, optxG = 255, optxB = 255;

void optxStop() {
    optxActive = false;
    ledOff();
    if (optxPayload) { free(optxPayload); optxPayload = nullptr; }
}

void optxUpdate() {
    if (!optxActive) return;
    
    uint32_t now = millis();
    if (now - optxLastSymbol < optxPeriod) return;
    optxLastSymbol = now;
    
    if (optxByteIdx >= optxLen) {
        if (optxRepeat) {
            optxByteIdx = 0;
            optxBitIdx = 0;
        } else {
            optxStop();
            return;
        }
    }
    
    bool bit = (optxPayload[optxByteIdx] >> (7 - optxBitIdx)) & 0x01;
    if (bit) {
        ledSetRGB(optxR, optxG, optxB);
    } else {
        ledOff();
    }
    
    optxBitIdx++;
    if (optxBitIdx >= 8) {
        optxBitIdx = 0;
        optxByteIdx++;
    }
}

// =============================================================================
// ACOUSTIC MODEM
// =============================================================================

static bool aotxActive = false;
static uint8_t* aotxPayload = nullptr;
static size_t aotxLen = 0;
static size_t aotxByteIdx = 0;
static uint8_t aotxBitIdx = 0;
static uint32_t aotxLastSymbol = 0;
static uint16_t aotxSymbolMs = 30;
static uint16_t aotxF0 = 1800;
static uint16_t aotxF1 = 2400;
static bool aotxRepeat = false;

void aotxStop() {
    aotxActive = false;
    buzzerStop();
    if (aotxPayload) { free(aotxPayload); aotxPayload = nullptr; }
}

void aotxUpdate() {
    if (!aotxActive) return;
    
    uint32_t now = millis();
    if (now - aotxLastSymbol < aotxSymbolMs) return;
    aotxLastSymbol = now;
    
    if (aotxByteIdx >= aotxLen) {
        if (aotxRepeat) {
            aotxByteIdx = 0;
            aotxBitIdx = 0;
        } else {
            aotxStop();
            return;
        }
    }
    
    bool bit = (aotxPayload[aotxByteIdx] >> (7 - aotxBitIdx)) & 0x01;
    buzzerTone(bit ? aotxF1 : aotxF0, 0);
    
    aotxBitIdx++;
    if (aotxBitIdx >= 8) {
        aotxBitIdx = 0;
        aotxByteIdx++;
    }
}

// =============================================================================
// BASE64 DECODE
// =============================================================================

size_t base64Decode(const char* input, uint8_t* output, size_t maxLen) {
    static const char b64[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    size_t inputLen = strlen(input);
    size_t outputLen = 0;
    uint32_t buffer = 0;
    int bits = 0;
    
    for (size_t i = 0; i < inputLen && outputLen < maxLen; i++) {
        char c = input[i];
        if (c == '=') break;
        const char* p = strchr(b64, c);
        if (!p) continue;
        buffer = (buffer << 6) | (p - b64);
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            output[outputLen++] = (buffer >> bits) & 0xFF;
        }
    }
    return outputLen;
}

// =============================================================================
// COMMAND PARSER
// =============================================================================

static char cmdBuffer[CLI_BUFFER_SIZE];
static size_t cmdIndex = 0;

void processCommand(const char* line) {
    if (line[0] == '\0') return;
    
    // JSON command
    if (line[0] == '{') {
        StaticJsonDocument<512> doc;
        if (deserializeJson(doc, line)) {
            emitError("json", "parse error");
            return;
        }
        
        const char* cmd = doc["cmd"];
        if (!cmd) { emitError("json", "missing cmd"); return; }
        
        if (strcmp(cmd, "led.rgb") == 0) {
            ledSetRGB(doc["r"] | 0, doc["g"] | 0, doc["b"] | 0);
            emitAck("led.rgb");
        } else if (strcmp(cmd, "led.off") == 0) {
            ledOff();
            emitAck("led.off");
        } else if (strcmp(cmd, "buzz.tone") == 0) {
            buzzerTone(doc["hz"] | 1000, doc["ms"] | 100);
            emitAck("buzz.tone");
        } else if (strcmp(cmd, "buzz.pattern") == 0) {
            buzzerPattern(doc["name"]);
            emitAck("buzz.pattern");
        } else if (strcmp(cmd, "optx.start") == 0) {
            const char* payload_b64 = doc["payload_b64"];
            if (payload_b64) {
                if (optxPayload) free(optxPayload);
                optxPayload = (uint8_t*)malloc(256);
                optxLen = base64Decode(payload_b64, optxPayload, 256);
                optxByteIdx = 0;
                optxBitIdx = 0;
                optxPeriod = 1000 / (doc["rate_hz"] | 10);
                optxRepeat = doc["repeat"] | false;
                optxR = doc["rgb"][0] | 255;
                optxG = doc["rgb"][1] | 255;
                optxB = doc["rgb"][2] | 255;
                optxLastSymbol = millis();
                optxActive = true;
                emitAck("optx.start", "transmitting");
            }
        } else if (strcmp(cmd, "optx.stop") == 0) {
            optxStop();
            emitAck("optx.stop");
        } else if (strcmp(cmd, "aotx.start") == 0) {
            const char* payload_b64 = doc["payload_b64"];
            if (payload_b64) {
                if (aotxPayload) free(aotxPayload);
                aotxPayload = (uint8_t*)malloc(256);
                aotxLen = base64Decode(payload_b64, aotxPayload, 256);
                aotxByteIdx = 0;
                aotxBitIdx = 0;
                aotxSymbolMs = doc["symbol_ms"] | 30;
                aotxF0 = doc["f0"] | 1800;
                aotxF1 = doc["f1"] | 2400;
                aotxRepeat = doc["repeat"] | false;
                aotxLastSymbol = millis();
                aotxActive = true;
                emitAck("aotx.start", "transmitting");
            }
        } else if (strcmp(cmd, "aotx.stop") == 0) {
            aotxStop();
            emitAck("aotx.stop");
        } else {
            emitError("json", "unknown command");
        }
        return;
    }
    
    // Parse CLI command
    static char lineCopy[CLI_BUFFER_SIZE];
    strncpy(lineCopy, line, CLI_BUFFER_SIZE - 1);
    
    static const char* argv[16];
    int argc = 0;
    char* token = strtok(lineCopy, " \t");
    while (token && argc < 16) {
        argv[argc++] = token;
        token = strtok(nullptr, " \t");
    }
    if (argc == 0) return;
    
    // Command routing
    if (strcmp(argv[0], "help") == 0) {
        if (currentMode == OpMode::HUMAN) {
            Serial.println("\n=== MycoBrain Advanced Commands ===");
            Serial.println("  help        - Show this help");
            Serial.println("  mode        - Set mode: human|machine");
            Serial.println("  status      - Get system status");
            Serial.println("  led         - LED control: rgb|off|status");
            Serial.println("  buzz        - Buzzer: tone|pattern|stop");
            Serial.println("  optx        - Optical modem: start|stop|status");
            Serial.println("  aotx        - Audio modem: start|stop|status");
            Serial.println("  periph      - Peripherals: scan|list");
            Serial.println("  out         - Outputs: set <1|2|3> <0|1>");
            Serial.println("  coin, morgio - Pattern aliases");
            Serial.println();
        } else {
            StaticJsonDocument<512> doc;
            doc["type"] = "help";
            JsonArray cmds = doc["commands"].to<JsonArray>();
            cmds.add("help"); cmds.add("mode"); cmds.add("status");
            cmds.add("led"); cmds.add("buzz"); cmds.add("optx");
            cmds.add("aotx"); cmds.add("periph"); cmds.add("out");
            serializeJson(doc, Serial);
            Serial.println();
        }
    }
    else if (strcmp(argv[0], "mode") == 0) {
        if (argc >= 2) {
            if (strcmp(argv[1], "machine") == 0) {
                currentMode = OpMode::MACHINE;
                emitAck("mode", "machine");
            } else if (strcmp(argv[1], "human") == 0) {
                currentMode = OpMode::HUMAN;
                Serial.println("Human mode enabled. Type 'help' for commands.");
            }
        }
    }
    else if (strcmp(argv[0], "status") == 0) {
        emitStatus();
    }
    else if (strcmp(argv[0], "led") == 0) {
        if (argc >= 2) {
            if (strcmp(argv[1], "rgb") == 0 && argc >= 5) {
                ledSetRGB(atoi(argv[2]), atoi(argv[3]), atoi(argv[4]));
                StaticJsonDocument<128> doc;
                doc["type"] = "ack"; doc["cmd"] = "led";
                doc["r"] = ledR; doc["g"] = ledG; doc["b"] = ledB;
                serializeJson(doc, Serial); Serial.println();
            } else if (strcmp(argv[1], "off") == 0) {
                ledOff();
                emitAck("led", "off");
            } else if (strcmp(argv[1], "status") == 0) {
                StaticJsonDocument<128> doc;
                doc["type"] = "status"; doc["cmd"] = "led";
                doc["r"] = ledR; doc["g"] = ledG; doc["b"] = ledB; doc["on"] = ledOn;
                serializeJson(doc, Serial); Serial.println();
            }
        }
    }
    else if (strcmp(argv[0], "buzz") == 0) {
        if (argc >= 2) {
            if (strcmp(argv[1], "tone") == 0 && argc >= 4) {
                buzzerTone(atoi(argv[2]), atoi(argv[3]));
                emitAck("buzz", "tone");
            } else if (strcmp(argv[1], "pattern") == 0 && argc >= 3) {
                buzzerPattern(argv[2]);
                emitAck("buzz", argv[2]);
            } else if (strcmp(argv[1], "stop") == 0) {
                buzzerStop();
                emitAck("buzz", "stopped");
            }
        }
    }
    else if (strcmp(argv[0], "optx") == 0) {
        if (argc >= 2) {
            if (strcmp(argv[1], "stop") == 0) {
                optxStop();
                emitAck("optx", "stopped");
            } else if (strcmp(argv[1], "status") == 0) {
                StaticJsonDocument<128> doc;
                doc["type"] = "status"; doc["cmd"] = "optx";
                doc["active"] = optxActive;
                serializeJson(doc, Serial); Serial.println();
            }
        }
    }
    else if (strcmp(argv[0], "aotx") == 0) {
        if (argc >= 2) {
            if (strcmp(argv[1], "stop") == 0) {
                aotxStop();
                emitAck("aotx", "stopped");
            } else if (strcmp(argv[1], "status") == 0) {
                StaticJsonDocument<128> doc;
                doc["type"] = "status"; doc["cmd"] = "aotx";
                doc["active"] = aotxActive;
                serializeJson(doc, Serial); Serial.println();
            }
        }
    }
    else if (strcmp(argv[0], "periph") == 0) {
        if (argc >= 2) {
            if (strcmp(argv[1], "scan") == 0 || strcmp(argv[1], "list") == 0) {
                scanI2C();
            }
        }
    }
    else if (strcmp(argv[0], "out") == 0) {
        if (argc >= 4 && strcmp(argv[1], "set") == 0) {
            int ch = atoi(argv[2]);
            int val = atoi(argv[3]);
            int pin = (ch == 1) ? PIN_OUT_1 : (ch == 2) ? PIN_OUT_2 : (ch == 3) ? PIN_OUT_3 : -1;
            if (pin >= 0) {
                digitalWrite(pin, val ? HIGH : LOW);
                StaticJsonDocument<128> doc;
                doc["type"] = "ack"; doc["cmd"] = "out";
                doc["channel"] = ch; doc["value"] = val;
                serializeJson(doc, Serial); Serial.println();
            }
        }
    }
    else if (strcmp(argv[0], "coin") == 0) {
        buzzerPattern("coin");
        emitAck("coin");
    }
    else if (strcmp(argv[0], "morgio") == 0) {
        buzzerPattern("morgio");
        emitAck("morgio");
    }
    else {
        if (currentMode == OpMode::MACHINE) {
            emitError(argv[0], "unknown command");
        } else {
            Serial.print("Unknown: "); Serial.println(argv[0]);
            Serial.println("Type 'help' for commands.");
        }
    }
}

// =============================================================================
// SETUP
// =============================================================================

void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(100);
    
    // Wait for serial (with timeout)
    uint32_t start = millis();
    while (!Serial && (millis() - start) < 3000) delay(10);
    
    // Initialize NeoPixel
    strip.Begin();
    strip.Show();
    
    // Initialize Buzzer
    ledcSetup(BUZZER_CHANNEL, 1000, 8);
    ledcAttachPin(PIN_BUZZER, BUZZER_CHANNEL);
    
    // Initialize I2C
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.setClock(100000);
    
    // Initialize outputs
    pinMode(PIN_OUT_1, OUTPUT); digitalWrite(PIN_OUT_1, LOW);
    pinMode(PIN_OUT_2, OUTPUT); digitalWrite(PIN_OUT_2, LOW);
    pinMode(PIN_OUT_3, OUTPUT); digitalWrite(PIN_OUT_3, LOW);
    
    // Boot sequence
    ledSetRGB(0, 0, 255); delay(100);
    ledSetRGB(0, 255, 0); delay(100);
    ledSetRGB(255, 255, 0); delay(100);
    ledOff();
    
    buzzerPattern("morgio");
    
    // Print banner
    Serial.println();
    Serial.println("╔═══════════════════════════════════════════╗");
    Serial.println("║  MycoBrain Advanced Firmware v2.0         ║");
    Serial.println("║  Science Communication Platform           ║");
    Serial.println("╚═══════════════════════════════════════════╝");
    Serial.println();
    
    uint64_t mac = ESP.getEfuseMac();
    Serial.printf("MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
        (uint8_t)(mac >> 40), (uint8_t)(mac >> 32),
        (uint8_t)(mac >> 24), (uint8_t)(mac >> 16),
        (uint8_t)(mac >> 8), (uint8_t)mac);
    Serial.println("Type 'help' for commands, 'mode machine' for JSON mode.");
    Serial.println();
}

// =============================================================================
// LOOP
// =============================================================================

static uint32_t lastTelemetry = 0;

void loop() {
    // Process serial input
    while (Serial.available()) {
        char c = Serial.read();
        if (c == '\n' || c == '\r') {
            if (cmdIndex > 0) {
                cmdBuffer[cmdIndex] = '\0';
                processCommand(cmdBuffer);
                cmdIndex = 0;
            }
        } else if (cmdIndex < CLI_BUFFER_SIZE - 1) {
            cmdBuffer[cmdIndex++] = c;
        }
    }
    
    // Update modems
    optxUpdate();
    aotxUpdate();
    
    // Periodic telemetry in machine mode
    if (currentMode == OpMode::MACHINE) {
        if (millis() - lastTelemetry >= 1000) {
            lastTelemetry = millis();
            StaticJsonDocument<256> doc;
            doc["type"] = "telemetry";
            doc["uptime_ms"] = millis();
            doc["led"]["on"] = ledOn;
            doc["optx_active"] = optxActive;
            doc["aotx_active"] = aotxActive;
            serializeJson(doc, Serial);
            Serial.println();
        }
    }
    
    yield();
}

