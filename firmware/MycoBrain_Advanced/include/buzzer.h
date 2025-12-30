/**
 * MycoBrain Advanced Firmware - Buzzer Module
 * 
 * Piezo buzzer control with tone generation and pattern engine.
 * Uses ESP32 LEDC for PWM tone generation on GPIO16.
 * 
 * @author Mycosoft
 * @version 2.0.0
 */

#ifndef MYCOBRAIN_BUZZER_H
#define MYCOBRAIN_BUZZER_H

#include <Arduino.h>
#include "config.h"

namespace buzzer {

// =============================================================================
// INITIALIZATION
// =============================================================================
void init();

// =============================================================================
// BASIC CONTROL
// =============================================================================

// Play a tone at specified frequency for duration (blocking if duration > 0)
void tone(uint16_t frequency, uint16_t duration_ms = 0);

// Stop current tone
void stop();

// Check if buzzer is active
bool isPlaying();

// =============================================================================
// PATTERN ENGINE (non-blocking)
// =============================================================================

enum class Pattern {
    NONE,
    COIN,           // Mario coin sound
    BUMP,           // Mario bump sound
    POWER,          // Power-up sound
    ONE_UP,         // 1-UP sound
    MORGIO,         // Morgio jingle
    ALERT,          // Alert beeps
    WARNING,        // Warning tone
    SUCCESS,        // Success melody
    ERROR_TONE,     // Error buzz
    CHIRP,          // Quick chirp
    SWEEP_UP,       // Frequency sweep up
    SWEEP_DOWN,     // Frequency sweep down
    PULSE_TRAIN,    // Pulsed tone
    MORSE           // Morse code pattern
};

// Start a pattern (non-blocking)
void startPattern(Pattern pattern);

// Stop current pattern
void stopPattern();

// Get current pattern state
Pattern getCurrentPattern();
bool isPatternRunning();

// =============================================================================
// CUSTOM PATTERN
// =============================================================================

struct Note {
    uint16_t frequency;     // Hz (0 = rest)
    uint16_t duration_ms;   // Duration
};

// Play a custom sequence of notes (non-blocking)
void playSequence(const Note* notes, size_t count, bool loop = false);

// =============================================================================
// SCHEDULER TICK
// Call this from the main loop for pattern updates
// =============================================================================
void update();

// =============================================================================
// STATUS
// =============================================================================
void getStatus(bool& playing, Pattern& pattern, uint16_t& frequency);

} // namespace buzzer

#endif // MYCOBRAIN_BUZZER_H

