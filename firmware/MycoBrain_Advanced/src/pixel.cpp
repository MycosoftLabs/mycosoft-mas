/**
 * MycoBrain Advanced Firmware - NeoPixel Implementation
 * 
 * Uses NeoPixelBus library with RMT driver for ESP32-S3.
 * Onboard LED is SK6805 on GPIO15.
 */

#include "pixel.h"
#include <NeoPixelBus.h>

namespace pixel {

// =============================================================================
// HARDWARE CONFIGURATION
// =============================================================================
// NeoPixelBus with GRB color order (standard for WS2812/SK6805)
// Using RMT channel for accurate timing on ESP32-S3
static NeoPixelBus<NeoGrbFeature, NeoEsp32Rmt0Ws2812xMethod> strip(NEOPIXEL_COUNT, PIN_NEOPIXEL);

// =============================================================================
// STATE
// =============================================================================
static uint8_t currentR = 0;
static uint8_t currentG = 0;
static uint8_t currentB = 0;
static bool ledOn = false;
static Pattern currentPattern = Pattern::NONE;
static uint32_t patternStartTime = 0;
static uint16_t patternTempo = 500;
static uint8_t patternR = 255, patternG = 255, patternB = 255;
static uint8_t patternPhase = 0;

// =============================================================================
// INITIALIZATION
// =============================================================================
void init() {
    strip.Begin();
    strip.Show();  // Initialize all pixels to 'off'
    currentR = currentG = currentB = 0;
    ledOn = false;
    currentPattern = Pattern::NONE;
}

// =============================================================================
// BASIC CONTROL
// =============================================================================

void setRGB(uint8_t r, uint8_t g, uint8_t b) {
    currentR = r;
    currentG = g;
    currentB = b;
    ledOn = (r > 0 || g > 0 || b > 0);
    
    strip.SetPixelColor(0, RgbColor(r, g, b));
    strip.Show();
}

void setRGBBrightness(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) {
    // Scale colors by brightness (0-255)
    uint8_t scaledR = (r * brightness) / 255;
    uint8_t scaledG = (g * brightness) / 255;
    uint8_t scaledB = (b * brightness) / 255;
    setRGB(scaledR, scaledG, scaledB);
}

void off() {
    setRGB(0, 0, 0);
    ledOn = false;
}

void getColor(uint8_t& r, uint8_t& g, uint8_t& b) {
    r = currentR;
    g = currentG;
    b = currentB;
}

bool isOn() {
    return ledOn;
}

// =============================================================================
// PATTERN ENGINE
// =============================================================================

void startPattern(Pattern pattern, uint16_t tempo_ms, uint8_t r, uint8_t g, uint8_t b) {
    currentPattern = pattern;
    patternTempo = tempo_ms;
    patternR = r;
    patternG = g;
    patternB = b;
    patternStartTime = millis();
    patternPhase = 0;
}

void stopPattern() {
    currentPattern = Pattern::NONE;
    off();
}

Pattern getCurrentPattern() {
    return currentPattern;
}

bool isPatternRunning() {
    return currentPattern != Pattern::NONE;
}

void update() {
    if (currentPattern == Pattern::NONE) return;
    
    uint32_t elapsed = millis() - patternStartTime;
    
    switch (currentPattern) {
        case Pattern::PULSE: {
            // Sine wave pulse effect
            float phase = (float)(elapsed % patternTempo) / patternTempo;
            float brightness = (sin(phase * 2 * PI) + 1.0f) / 2.0f;
            setRGBBrightness(patternR, patternG, patternB, (uint8_t)(brightness * 255));
            break;
        }
        
        case Pattern::SWEEP: {
            // Color sweep through hue spectrum
            float hue = (float)(elapsed % patternTempo) / patternTempo;
            // HSV to RGB (simplified)
            int h = (int)(hue * 6);
            float f = hue * 6 - h;
            uint8_t v = 255;
            uint8_t p = 0;
            uint8_t q = (uint8_t)(255 * (1 - f));
            uint8_t t = (uint8_t)(255 * f);
            
            switch (h % 6) {
                case 0: setRGB(v, t, p); break;
                case 1: setRGB(q, v, p); break;
                case 2: setRGB(p, v, t); break;
                case 3: setRGB(p, q, v); break;
                case 4: setRGB(t, p, v); break;
                case 5: setRGB(v, p, q); break;
            }
            break;
        }
        
        case Pattern::BEACON: {
            // Periodic flash
            uint32_t cyclePos = elapsed % patternTempo;
            if (cyclePos < patternTempo / 10) {
                setRGB(patternR, patternG, patternB);
            } else {
                off();
            }
            break;
        }
        
        case Pattern::RAINBOW: {
            // Continuous rainbow cycle
            float hue = (float)(elapsed % (patternTempo * 6)) / (patternTempo * 6);
            int h = (int)(hue * 6);
            float f = hue * 6 - h;
            uint8_t v = 255;
            uint8_t p = 0;
            uint8_t q = (uint8_t)(255 * (1 - f));
            uint8_t t = (uint8_t)(255 * f);
            
            switch (h % 6) {
                case 0: setRGB(v, t, p); break;
                case 1: setRGB(q, v, p); break;
                case 2: setRGB(p, v, t); break;
                case 3: setRGB(p, q, v); break;
                case 4: setRGB(t, p, v); break;
                case 5: setRGB(v, p, q); break;
            }
            break;
        }
        
        case Pattern::BLINK: {
            // Simple on/off blink
            if ((elapsed / (patternTempo / 2)) % 2 == 0) {
                setRGB(patternR, patternG, patternB);
            } else {
                off();
            }
            break;
        }
        
        default:
            break;
    }
}

// =============================================================================
// STATUS
// =============================================================================
void getStatus(uint8_t& r, uint8_t& g, uint8_t& b, bool& on, Pattern& pattern) {
    r = currentR;
    g = currentG;
    b = currentB;
    on = ledOn;
    pattern = currentPattern;
}

} // namespace pixel

