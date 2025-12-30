/**
 * MycoBrain Advanced Firmware - NeoPixel Module
 * 
 * NeoPixelBus wrapper for onboard SK6805 LED and optional external arrays.
 * Uses ESP32-S3 RMT peripheral for timing-accurate WS2812 protocol.
 * 
 * IMPORTANT: The onboard LED is on GPIO15, NOT GPIO12/13/14!
 * 
 * @author Mycosoft
 * @version 2.0.0
 */

#ifndef MYCOBRAIN_PIXEL_H
#define MYCOBRAIN_PIXEL_H

#include <Arduino.h>
#include "config.h"

namespace pixel {

// =============================================================================
// INITIALIZATION
// =============================================================================
void init();

// =============================================================================
// BASIC CONTROL
// =============================================================================

// Set RGB color (0-255 each)
void setRGB(uint8_t r, uint8_t g, uint8_t b);

// Set color with brightness adjustment (0-255)
void setRGBBrightness(uint8_t r, uint8_t g, uint8_t b, uint8_t brightness);

// Turn off LED
void off();

// Get current color
void getColor(uint8_t& r, uint8_t& g, uint8_t& b);

// Get current state
bool isOn();

// =============================================================================
// PATTERN ENGINE (non-blocking)
// =============================================================================

enum class Pattern {
    NONE,
    PULSE,          // Fade in/out
    SWEEP,          // Color sweep through spectrum
    BEACON,         // Periodic flash
    MORSE,          // Morse code pattern
    RAINBOW,        // Rainbow cycle
    BLINK           // Simple on/off blink
};

// Start a pattern
void startPattern(Pattern pattern, uint16_t tempo_ms = 500, 
                  uint8_t r = 255, uint8_t g = 255, uint8_t b = 255);

// Stop current pattern
void stopPattern();

// Get current pattern state
Pattern getCurrentPattern();
bool isPatternRunning();

// =============================================================================
// SCHEDULER TICK
// Call this from the main loop for pattern updates
// =============================================================================
void update();

// =============================================================================
// STATUS
// =============================================================================
void getStatus(uint8_t& r, uint8_t& g, uint8_t& b, bool& on, Pattern& pattern);

} // namespace pixel

#endif // MYCOBRAIN_PIXEL_H

