/**
 * MycoBrain Advanced Firmware - Main Entry Point
 * 
 * ESP32-S3 based environmental sensing and science communication platform.
 * 
 * Features:
 * - NeoPixel LED control (SK6805 on GPIO15)
 * - Buzzer with patterns (GPIO16)
 * - Optical modem (LiFi TX via NeoPixel)
 * - Acoustic modem (FSK TX via buzzer)
 * - Stimulus engine for experiments
 * - Peripheral discovery (I2C)
 * - JSON-CLI / NDJSON protocol
 * 
 * @author Mycosoft
 * @version 2.0.0
 */

#include <Arduino.h>
#include "config.h"
#include "jsonio.h"
#include "cli.h"
#include "pixel.h"
#include "buzzer.h"
#include "modem_optical.h"
#include "modem_audio.h"
#include "peripherals.h"
#include "stimulus.h"

// =============================================================================
// BOOT BANNER
// =============================================================================
static const char* BOOT_BANNER = R"(
╔══════════════════════════════════════════════════════════════╗
║  ███╗   ███╗██╗   ██╗ ██████╗ ██████╗ ██████╗ ██████╗  █████╗ ██╗███╗   ██╗ ║
║  ████╗ ████║╚██╗ ██╔╝██╔════╝██╔═══██╗██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║ ║
║  ██╔████╔██║ ╚████╔╝ ██║     ██║   ██║██████╔╝██████╔╝███████║██║██╔██╗ ██║ ║
║  ██║╚██╔╝██║  ╚██╔╝  ██║     ██║   ██║██╔══██╗██╔══██╗██╔══██║██║██║╚██╗██║ ║
║  ██║ ╚═╝ ██║   ██║   ╚██████╗╚██████╔╝██████╔╝██║  ██║██║  ██║██║██║ ╚████║ ║
║  ╚═╝     ╚═╝   ╚═╝    ╚═════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ║
║  Advanced Science Communication Firmware v2.0                              ║
╚══════════════════════════════════════════════════════════════╝
)";

// =============================================================================
// TIMING
// =============================================================================
static uint32_t lastTelemetryTime = 0;
static uint32_t lastSchedulerTick = 0;

// =============================================================================
// SETUP
// =============================================================================
void setup() {
    // Initialize serial
    Serial.begin(SERIAL_BAUD);
    delay(100);  // Allow serial to stabilize
    
    // Wait for serial connection (with timeout)
    uint32_t startWait = millis();
    while (!Serial && (millis() - startWait) < 3000) {
        delay(10);
    }
    
    // Initialize all modules
    jsonio::init();
    pixel::init();
    buzzer::init();
    modem_optical::init();
    modem_audio::init();
    peripherals::init();
    stimulus::init();
    cli::init();
    
    // Configure GPIO outputs
    pinMode(PIN_OUT_1, OUTPUT);
    pinMode(PIN_OUT_2, OUTPUT);
    pinMode(PIN_OUT_3, OUTPUT);
    digitalWrite(PIN_OUT_1, LOW);
    digitalWrite(PIN_OUT_2, LOW);
    digitalWrite(PIN_OUT_3, LOW);
    
    // Boot indication
    pixel::setRGB(0, 0, 255);  // Blue
    delay(100);
    pixel::setRGB(0, 255, 0);  // Green
    delay(100);
    pixel::setRGB(255, 255, 0); // Yellow
    delay(100);
    pixel::off();
    
    // Play boot jingle
    buzzer::startPattern(buzzer::Pattern::MORGIO);
    
    // Print boot banner (human mode only)
    jsonio::printBanner(BOOT_BANNER);
    jsonio::printInfo("Type 'help' for commands, or 'mode machine' for JSON mode.");
    jsonio::printInfo("");
    
    // Get board MAC for identification
    uint64_t mac = ESP.getEfuseMac();
    char macStr[18];
    snprintf(macStr, sizeof(macStr), "%02X:%02X:%02X:%02X:%02X:%02X",
             (uint8_t)(mac >> 40), (uint8_t)(mac >> 32),
             (uint8_t)(mac >> 24), (uint8_t)(mac >> 16),
             (uint8_t)(mac >> 8), (uint8_t)mac);
    
    // Log startup in machine mode compatible format
    if (jsonio::isMachineMode()) {
        StaticJsonDocument<256> doc;
        doc["type"] = "boot";
        doc["firmware"] = FIRMWARE_NAME;
        doc["version"] = FIRMWARE_VERSION;
        doc["mac"] = macStr;
        doc["uptime_ms"] = millis();
        jsonio::emitJson(doc);
    } else {
        Serial.print("MAC: ");
        Serial.println(macStr);
        Serial.print("Firmware: ");
        Serial.print(FIRMWARE_NAME);
        Serial.print(" v");
        Serial.println(FIRMWARE_VERSION);
        Serial.println("");
    }
}

// =============================================================================
// MAIN LOOP
// =============================================================================
void loop() {
    uint32_t now = millis();
    
    // Process CLI input
    cli::update();
    
    // Update all modules (non-blocking)
    if (now - lastSchedulerTick >= SCHEDULER_TICK_MS) {
        lastSchedulerTick = now;
        
        pixel::update();
        buzzer::update();
        modem_optical::update();
        modem_audio::update();
        peripherals::update();
        stimulus::update();
    }
    
    // Emit periodic telemetry (machine mode only)
    if (jsonio::isMachineMode()) {
        if (now - lastTelemetryTime >= TELEMETRY_INTERVAL_MS) {
            lastTelemetryTime = now;
            
            StaticJsonDocument<512> doc;
            doc["uptime_ms"] = millis();
            
            // LED state
            uint8_t r, g, b;
            bool ledOn;
            pixel::Pattern ledPattern;
            pixel::getStatus(r, g, b, ledOn, ledPattern);
            doc["led"]["r"] = r;
            doc["led"]["g"] = g;
            doc["led"]["b"] = b;
            doc["led"]["on"] = ledOn;
            
            // Modem states
            bool optxActive, optxPattern;
            OpticalProfile optProfile;
            uint8_t optRate;
            modem_optical::getStatus(optxActive, optxPattern, optProfile, optRate);
            doc["optx_active"] = optxActive || optxPattern;
            
            bool aotxActive, aotxPattern;
            AcousticProfile aoProfile;
            uint16_t aoSymbol;
            modem_audio::getStatus(aotxActive, aotxPattern, aoProfile, aoSymbol);
            doc["aotx_active"] = aotxActive || aotxPattern;
            
            // Stimulus state
            bool stimLight, stimSound;
            uint32_t stimElapsed;
            uint16_t stimCycles;
            stimulus::getStatus(stimLight, stimSound, stimElapsed, stimCycles);
            doc["stim_active"] = stimLight || stimSound;
            
            // Peripheral count
            doc["periph_count"] = peripherals::getCount();
            
            jsonio::emitTelemetry(doc);
        }
    }
    
    // Small yield to prevent watchdog issues
    yield();
}

