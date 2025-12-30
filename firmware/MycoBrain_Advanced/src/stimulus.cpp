/**
 * MycoBrain Advanced Firmware - Stimulus Engine Implementation
 */

#include "stimulus.h"
#include "pixel.h"
#include "buzzer.h"
#include "jsonio.h"
#include <ArduinoJson.h>

namespace stimulus {

// =============================================================================
// STATE
// =============================================================================
static bool lightActive = false;
static LightStimulus lightConfig;
static uint32_t lightStartTime = 0;
static uint16_t lightCycleCount = 0;
static bool lightPhaseOn = false;
static uint32_t lightPhaseStart = 0;

static bool soundActive = false;
static SoundStimulus soundConfig;
static uint32_t soundStartTime = 0;
static uint16_t soundCycleCount = 0;
static bool soundPhaseOn = false;
static uint32_t soundPhaseStart = 0;

static bool loggingEnabled = false;

// Simple log buffer (last 16 events)
#define LOG_SIZE 16
struct LogEntry {
    uint32_t timestamp;
    char event[32];
};
static LogEntry logBuffer[LOG_SIZE];
static size_t logIndex = 0;
static size_t logCount = 0;

// =============================================================================
// LOGGING HELPERS
// =============================================================================
static void logEvent(const char* event) {
    if (!loggingEnabled) return;
    
    logBuffer[logIndex].timestamp = millis();
    strncpy(logBuffer[logIndex].event, event, sizeof(logBuffer[logIndex].event) - 1);
    logIndex = (logIndex + 1) % LOG_SIZE;
    if (logCount < LOG_SIZE) logCount++;
}

// =============================================================================
// INITIALIZATION
// =============================================================================
void init() {
    lightActive = false;
    soundActive = false;
    loggingEnabled = false;
    logCount = 0;
    logIndex = 0;
}

// =============================================================================
// LIGHT STIMULUS
// =============================================================================

bool startLight(const LightStimulus& config) {
    lightConfig = config;
    lightStartTime = millis();
    lightCycleCount = 0;
    lightPhaseOn = false;
    lightPhaseStart = 0;
    
    // Apply initial delay
    if (config.delay_ms > 0) {
        lightPhaseStart = millis();
    }
    
    lightActive = true;
    logEvent("light_start");
    return true;
}

void stopLight() {
    lightActive = false;
    pixel::off();
    logEvent("light_stop");
}

bool isLightActive() {
    return lightActive;
}

// =============================================================================
// SOUND STIMULUS
// =============================================================================

bool startSound(const SoundStimulus& config) {
    soundConfig = config;
    soundStartTime = millis();
    soundCycleCount = 0;
    soundPhaseOn = false;
    soundPhaseStart = 0;
    
    // Apply initial delay
    if (config.delay_ms > 0) {
        soundPhaseStart = millis();
    }
    
    soundActive = true;
    logEvent("sound_start");
    return true;
}

void stopSound() {
    soundActive = false;
    buzzer::stop();
    logEvent("sound_stop");
}

bool isSoundActive() {
    return soundActive;
}

// =============================================================================
// COMBINED STIMULUS
// =============================================================================

bool startCombined(const CombinedStimulus& config) {
    bool lightOk = startLight(config.light);
    bool soundOk = startSound(config.sound);
    
    if (config.sync) {
        // Synchronize start times
        uint32_t now = millis();
        lightStartTime = now;
        soundStartTime = now;
    }
    
    return lightOk && soundOk;
}

void stopAll() {
    stopLight();
    stopSound();
}

// =============================================================================
// LOGGING
// =============================================================================

void setLogging(bool enabled) {
    loggingEnabled = enabled;
}

void getLog(JsonDocument& doc) {
    doc["type"] = "stimulus_log";
    doc["count"] = logCount;
    
    JsonArray events = doc["events"].to<JsonArray>();
    for (size_t i = 0; i < logCount; i++) {
        size_t idx = (logIndex - logCount + i + LOG_SIZE) % LOG_SIZE;
        JsonObject entry = events.add<JsonObject>();
        entry["t"] = logBuffer[idx].timestamp;
        entry["e"] = logBuffer[idx].event;
    }
}

void clearLog() {
    logCount = 0;
    logIndex = 0;
}

// =============================================================================
// UPDATE
// =============================================================================

void update() {
    uint32_t now = millis();
    
    // Light stimulus update
    if (lightActive) {
        uint32_t elapsed = now - lightStartTime;
        
        // Handle initial delay
        if (elapsed < lightConfig.delay_ms) {
            // Still in delay phase
        } else {
            uint32_t stimulusTime = elapsed - lightConfig.delay_ms;
            uint32_t cycleDuration = lightConfig.on_ms + lightConfig.off_ms;
            uint32_t cyclePos = stimulusTime % cycleDuration;
            
            // Check if we completed a cycle
            uint16_t currentCycle = stimulusTime / cycleDuration;
            if (currentCycle > lightCycleCount) {
                lightCycleCount = currentCycle;
                logEvent("light_cycle");
                
                // Check repeat count
                if (lightConfig.repeat_count > 0 && lightCycleCount >= lightConfig.repeat_count) {
                    stopLight();
                    return;
                }
            }
            
            // Determine phase (on or off)
            if (cyclePos < lightConfig.on_ms) {
                // ON phase
                if (!lightPhaseOn) {
                    lightPhaseOn = true;
                    logEvent("light_on");
                }
                
                // Handle ramp
                if (lightConfig.ramp_ms > 0 && cyclePos < lightConfig.ramp_ms) {
                    // Ramp up
                    float brightness = (float)cyclePos / lightConfig.ramp_ms;
                    pixel::setRGBBrightness(lightConfig.color_r, lightConfig.color_g, 
                                           lightConfig.color_b, (uint8_t)(brightness * 255));
                } else if (lightConfig.ramp_ms > 0 && 
                          (lightConfig.on_ms - cyclePos) < lightConfig.ramp_ms) {
                    // Ramp down
                    float brightness = (float)(lightConfig.on_ms - cyclePos) / lightConfig.ramp_ms;
                    pixel::setRGBBrightness(lightConfig.color_r, lightConfig.color_g,
                                           lightConfig.color_b, (uint8_t)(brightness * 255));
                } else {
                    pixel::setRGB(lightConfig.color_r, lightConfig.color_g, lightConfig.color_b);
                }
            } else {
                // OFF phase
                if (lightPhaseOn) {
                    lightPhaseOn = false;
                    logEvent("light_off");
                }
                pixel::off();
            }
        }
    }
    
    // Sound stimulus update
    if (soundActive) {
        uint32_t elapsed = now - soundStartTime;
        
        // Handle initial delay
        if (elapsed < soundConfig.delay_ms) {
            // Still in delay phase
        } else {
            uint32_t stimulusTime = elapsed - soundConfig.delay_ms;
            uint32_t cycleDuration = soundConfig.on_ms + soundConfig.off_ms;
            uint32_t cyclePos = stimulusTime % cycleDuration;
            
            // Check if we completed a cycle
            uint16_t currentCycle = stimulusTime / cycleDuration;
            if (currentCycle > soundCycleCount) {
                soundCycleCount = currentCycle;
                logEvent("sound_cycle");
                
                // Check repeat count
                if (soundConfig.repeat_count > 0 && soundCycleCount >= soundConfig.repeat_count) {
                    stopSound();
                    return;
                }
            }
            
            // Determine phase (on or off)
            if (cyclePos < soundConfig.on_ms) {
                // ON phase
                if (!soundPhaseOn) {
                    soundPhaseOn = true;
                    logEvent("sound_on");
                }
                
                // Handle frequency sweep
                uint16_t freq = soundConfig.frequency;
                if (soundConfig.freq_sweep_hz > 0) {
                    float progress = (float)cyclePos / soundConfig.on_ms;
                    freq = soundConfig.frequency + 
                           (uint16_t)(sin(progress * PI) * soundConfig.freq_sweep_hz);
                }
                
                buzzer::tone(freq, 0);
            } else {
                // OFF phase
                if (soundPhaseOn) {
                    soundPhaseOn = false;
                    logEvent("sound_off");
                }
                buzzer::stop();
            }
        }
    }
}

// =============================================================================
// STATUS
// =============================================================================

void getStatus(bool& light_active, bool& sound_active,
               uint32_t& elapsed_ms, uint16_t& cycle_count) {
    light_active = lightActive;
    sound_active = soundActive;
    
    if (lightActive) {
        elapsed_ms = millis() - lightStartTime;
        cycle_count = lightCycleCount;
    } else if (soundActive) {
        elapsed_ms = millis() - soundStartTime;
        cycle_count = soundCycleCount;
    } else {
        elapsed_ms = 0;
        cycle_count = 0;
    }
}

} // namespace stimulus

