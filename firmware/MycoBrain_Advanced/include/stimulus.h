/**
 * MycoBrain Advanced Firmware - Stimulus Engine Module
 * 
 * Controlled stimulus patterns for scientific experiments with organisms.
 * Separate from modem mode to ensure repeatability and avoid decoding conflicts.
 * 
 * Supports:
 * - Light stimulus patterns (via NeoPixel)
 * - Sound stimulus patterns (via Buzzer)
 * - Combined multi-modal stimuli
 * - Precise timing and logging
 * 
 * @author Mycosoft
 * @version 2.0.0
 */

#ifndef MYCOBRAIN_STIMULUS_H
#define MYCOBRAIN_STIMULUS_H

#include <Arduino.h>
#include "config.h"

namespace stimulus {

// =============================================================================
// INITIALIZATION
// =============================================================================
void init();

// =============================================================================
// LIGHT STIMULUS
// =============================================================================

struct LightStimulus {
    uint8_t color_r;
    uint8_t color_g;
    uint8_t color_b;
    uint16_t on_ms;             // Duration LED is on
    uint16_t off_ms;            // Duration LED is off
    uint16_t ramp_ms;           // Fade in/out time (0 = instant)
    uint16_t repeat_count;      // 0 = infinite
    uint32_t delay_ms;          // Initial delay before starting
};

// Start light stimulus
bool startLight(const LightStimulus& config);

// Stop light stimulus
void stopLight();

// Check if light stimulus is active
bool isLightActive();

// =============================================================================
// SOUND STIMULUS
// =============================================================================

struct SoundStimulus {
    uint16_t frequency;         // Hz
    uint16_t on_ms;             // Duration tone is on
    uint16_t off_ms;            // Duration tone is off
    uint16_t freq_sweep_hz;     // Frequency modulation range (0 = fixed)
    uint16_t repeat_count;      // 0 = infinite
    uint32_t delay_ms;          // Initial delay before starting
};

// Start sound stimulus
bool startSound(const SoundStimulus& config);

// Stop sound stimulus
void stopSound();

// Check if sound stimulus is active
bool isSoundActive();

// =============================================================================
// COMBINED STIMULUS
// =============================================================================

struct CombinedStimulus {
    LightStimulus light;
    SoundStimulus sound;
    bool sync;                  // Synchronize light and sound
};

// Start combined stimulus
bool startCombined(const CombinedStimulus& config);

// Stop all stimuli
void stopAll();

// =============================================================================
// STIMULUS LOGGING
// =============================================================================

// Enable/disable stimulus event logging
void setLogging(bool enabled);

// Get log (JSON format)
void getLog(JsonDocument& doc);

// Clear log
void clearLog();

// =============================================================================
// SCHEDULER TICK
// Call from main loop for timing updates
// =============================================================================
void update();

// =============================================================================
// STATUS
// =============================================================================
void getStatus(bool& light_active, bool& sound_active,
               uint32_t& elapsed_ms, uint16_t& cycle_count);

} // namespace stimulus

#endif // MYCOBRAIN_STIMULUS_H

