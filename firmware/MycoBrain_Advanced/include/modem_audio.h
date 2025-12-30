/**
 * MycoBrain Advanced Firmware - Acoustic Modem Module
 * 
 * Acoustic data transmission using buzzer for microphone receivers.
 * Inspired by ggwave/gibberlink for audio-based data transfer.
 * 
 * Profiles:
 * - SIMPLE_FSK: 2-tone FSK with preamble + CRC16 (robust, simple)
 * - GGWAVE_LIKE: Multi-tone encoding (planned, more robust)
 * 
 * @author Mycosoft
 * @version 2.0.0
 */

#ifndef MYCOBRAIN_MODEM_AUDIO_H
#define MYCOBRAIN_MODEM_AUDIO_H

#include <Arduino.h>
#include "config.h"

namespace modem_audio {

// =============================================================================
// INITIALIZATION
// =============================================================================
void init();

// =============================================================================
// TRANSMISSION CONTROL
// =============================================================================

struct TxConfig {
    AcousticProfile profile;
    uint16_t symbol_ms;         // Symbol duration (30-100ms typical)
    uint16_t freq_0;            // Frequency for bit 0 (e.g., 1800 Hz)
    uint16_t freq_1;            // Frequency for bit 1 (e.g., 2400 Hz)
    uint8_t* payload;           // Data to transmit
    size_t payload_len;
    bool repeat;                // Loop transmission
    bool include_crc;           // Add CRC16 to payload
    uint16_t preamble_freq;     // Preamble tone frequency
    uint16_t preamble_ms;       // Preamble duration
};

// Start data transmission
bool startTx(const TxConfig& config);

// Stop transmission
void stopTx();

// Check if transmitting
bool isTxActive();

// Get transmission status
void getTxStatus(bool& active, size_t& bytes_sent, size_t& total_bytes,
                 uint8_t& current_bit, bool& crc_ok);

// =============================================================================
// PATTERN MODE (non-data audio patterns)
// =============================================================================

enum class AudioPattern {
    NONE,
    SWEEP,          // Frequency sweep
    CHIRP,          // Chirp signal
    PULSE_TRAIN,    // Pulsed tones
    MORSE,          // Morse code
    DTMF,           // DTMF-like tones
    SIREN           // Alternating tones
};

struct PatternConfig {
    AudioPattern pattern;
    uint16_t freq_start;
    uint16_t freq_end;
    uint16_t duration_ms;
    uint16_t tempo_ms;
    bool repeat;
    const char* morse_text;     // For MORSE pattern
};

// Start an audio pattern
void startPattern(const PatternConfig& config);

// Stop pattern
void stopPattern();

// Check if pattern is running
bool isPatternActive();

// =============================================================================
// SCHEDULER TICK
// Call from main loop for non-blocking operation
// =============================================================================
void update();

// =============================================================================
// STATUS
// =============================================================================
void getStatus(bool& tx_active, bool& pattern_active,
               AcousticProfile& profile, uint16_t& symbol_ms);

} // namespace modem_audio

#endif // MYCOBRAIN_MODEM_AUDIO_H

