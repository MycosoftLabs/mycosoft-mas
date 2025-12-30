/**
 * MycoBrain Advanced Firmware - Buzzer Implementation
 * 
 * Uses ESP32 LEDC for PWM tone generation on GPIO16.
 */

#include "buzzer.h"

namespace buzzer {

// =============================================================================
// LEDC CONFIGURATION
// =============================================================================
#define BUZZER_CHANNEL  0
#define BUZZER_RESOLUTION 8

// =============================================================================
// STATE
// =============================================================================
static bool playing = false;
static Pattern currentPattern = Pattern::NONE;
static uint32_t patternStartTime = 0;
static uint8_t noteIndex = 0;
static uint32_t noteStartTime = 0;
static const Note* sequenceNotes = nullptr;
static size_t sequenceLength = 0;
static bool sequenceLoop = false;

// =============================================================================
// PREDEFINED PATTERNS
// =============================================================================

// Mario Coin sound
static const Note coinNotes[] = {
    {988, 100},   // B5
    {1319, 300}   // E6
};

// Mario Bump sound
static const Note bumpNotes[] = {
    {200, 50},
    {150, 50}
};

// Power-up sound
static const Note powerNotes[] = {
    {523, 50}, {659, 50}, {784, 50}, {1047, 50},
    {1319, 50}, {1568, 50}, {2093, 150}
};

// 1-UP sound
static const Note oneUpNotes[] = {
    {1319, 100}, {1568, 100}, {2637, 100},
    {2093, 100}, {2349, 100}, {3136, 200}
};

// Morgio Jingle
static const Note morgioNotes[] = {
    {659, 150}, {0, 50},    // E5
    {784, 150}, {0, 50},    // G5
    {880, 150}, {0, 50},    // A5
    {784, 150}, {0, 50},    // G5
    {659, 300}, {0, 100},   // E5
    {523, 150}, {0, 50},    // C5
    {587, 150}, {0, 50},    // D5
    {659, 400}              // E5
};

// Alert beeps
static const Note alertNotes[] = {
    {2000, 100}, {0, 100},
    {2000, 100}, {0, 100},
    {2000, 100}, {0, 400}
};

// Warning tone
static const Note warningNotes[] = {
    {800, 200}, {600, 200},
    {800, 200}, {600, 200}
};

// Success melody
static const Note successNotes[] = {
    {523, 100}, {659, 100}, {784, 200}
};

// Error buzz
static const Note errorNotes[] = {
    {200, 150}, {0, 50},
    {200, 150}
};

// =============================================================================
// INITIALIZATION
// =============================================================================
void init() {
    ledcSetup(BUZZER_CHANNEL, 1000, BUZZER_RESOLUTION);
    ledcAttachPin(PIN_BUZZER, BUZZER_CHANNEL);
    ledcWrite(BUZZER_CHANNEL, 0);
    playing = false;
    currentPattern = Pattern::NONE;
}

// =============================================================================
// BASIC CONTROL
// =============================================================================

void tone(uint16_t frequency, uint16_t duration_ms) {
    if (frequency == 0) {
        ledcWrite(BUZZER_CHANNEL, 0);
        playing = false;
    } else {
        ledcWriteTone(BUZZER_CHANNEL, frequency);
        ledcWrite(BUZZER_CHANNEL, 127);  // 50% duty cycle
        playing = true;
    }
    
    if (duration_ms > 0) {
        delay(duration_ms);
        stop();
    }
}

void stop() {
    ledcWrite(BUZZER_CHANNEL, 0);
    playing = false;
}

bool isPlaying() {
    return playing;
}

// =============================================================================
// PATTERN ENGINE
// =============================================================================

void startPattern(Pattern pattern) {
    currentPattern = pattern;
    patternStartTime = millis();
    noteIndex = 0;
    noteStartTime = millis();
    
    // Set up sequence based on pattern
    switch (pattern) {
        case Pattern::COIN:
            sequenceNotes = coinNotes;
            sequenceLength = sizeof(coinNotes) / sizeof(Note);
            sequenceLoop = false;
            break;
        case Pattern::BUMP:
            sequenceNotes = bumpNotes;
            sequenceLength = sizeof(bumpNotes) / sizeof(Note);
            sequenceLoop = false;
            break;
        case Pattern::POWER:
            sequenceNotes = powerNotes;
            sequenceLength = sizeof(powerNotes) / sizeof(Note);
            sequenceLoop = false;
            break;
        case Pattern::ONE_UP:
            sequenceNotes = oneUpNotes;
            sequenceLength = sizeof(oneUpNotes) / sizeof(Note);
            sequenceLoop = false;
            break;
        case Pattern::MORGIO:
            sequenceNotes = morgioNotes;
            sequenceLength = sizeof(morgioNotes) / sizeof(Note);
            sequenceLoop = false;
            break;
        case Pattern::ALERT:
            sequenceNotes = alertNotes;
            sequenceLength = sizeof(alertNotes) / sizeof(Note);
            sequenceLoop = false;
            break;
        case Pattern::WARNING:
            sequenceNotes = warningNotes;
            sequenceLength = sizeof(warningNotes) / sizeof(Note);
            sequenceLoop = true;
            break;
        case Pattern::SUCCESS:
            sequenceNotes = successNotes;
            sequenceLength = sizeof(successNotes) / sizeof(Note);
            sequenceLoop = false;
            break;
        case Pattern::ERROR_TONE:
            sequenceNotes = errorNotes;
            sequenceLength = sizeof(errorNotes) / sizeof(Note);
            sequenceLoop = false;
            break;
        default:
            sequenceNotes = nullptr;
            sequenceLength = 0;
            sequenceLoop = false;
            break;
    }
    
    // Start first note
    if (sequenceNotes && sequenceLength > 0) {
        tone(sequenceNotes[0].frequency, 0);
    }
}

void stopPattern() {
    currentPattern = Pattern::NONE;
    sequenceNotes = nullptr;
    sequenceLength = 0;
    stop();
}

Pattern getCurrentPattern() {
    return currentPattern;
}

bool isPatternRunning() {
    return currentPattern != Pattern::NONE;
}

void playSequence(const Note* notes, size_t count, bool loop) {
    sequenceNotes = notes;
    sequenceLength = count;
    sequenceLoop = loop;
    noteIndex = 0;
    noteStartTime = millis();
    currentPattern = Pattern::NONE;  // Custom sequence, not a named pattern
    
    if (notes && count > 0) {
        tone(notes[0].frequency, 0);
    }
}

void update() {
    if (sequenceNotes == nullptr || sequenceLength == 0) return;
    
    uint32_t elapsed = millis() - noteStartTime;
    
    if (elapsed >= sequenceNotes[noteIndex].duration_ms) {
        // Move to next note
        noteIndex++;
        
        if (noteIndex >= sequenceLength) {
            if (sequenceLoop) {
                noteIndex = 0;
            } else {
                stopPattern();
                return;
            }
        }
        
        noteStartTime = millis();
        tone(sequenceNotes[noteIndex].frequency, 0);
    }
}

// =============================================================================
// STATUS
// =============================================================================
void getStatus(bool& isPlaying, Pattern& pattern, uint16_t& frequency) {
    isPlaying = playing;
    pattern = currentPattern;
    frequency = 0;  // Would need to track current frequency
}

} // namespace buzzer

