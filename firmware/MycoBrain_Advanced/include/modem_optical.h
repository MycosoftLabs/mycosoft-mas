/**
 * MycoBrain Advanced Firmware - Optical Modem Module
 * 
 * LiFi-style optical transmission using NeoPixel LED for camera/light-sensor receivers.
 * Supports multiple encoding profiles optimized for different receiver types.
 * 
 * Profiles:
 * - CAMERA_OOK: Simple On-Off Keying (5-20 Hz for camera sync)
 * - CAMERA_MANCHESTER: Manchester encoding for better clock recovery
 * - SPATIAL_SM: Spatial modulation (requires multiple LEDs)
 * 
 * @author Mycosoft
 * @version 2.0.0
 */

#ifndef MYCOBRAIN_MODEM_OPTICAL_H
#define MYCOBRAIN_MODEM_OPTICAL_H

#include <Arduino.h>
#include "config.h"

namespace modem_optical {

// =============================================================================
// INITIALIZATION
// =============================================================================
void init();

// =============================================================================
// TRANSMISSION CONTROL
// =============================================================================

struct TxConfig {
    OpticalProfile profile;
    uint8_t rate_hz;            // Symbol rate (5-60 Hz typical for cameras)
    uint8_t* payload;           // Data to transmit
    size_t payload_len;
    bool repeat;                // Loop transmission
    uint8_t color_r;            // LED color
    uint8_t color_g;
    uint8_t color_b;
    bool include_crc;           // Add CRC16 to payload
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
// PATTERN MODE (non-data visual patterns)
// =============================================================================

enum class VisualPattern {
    NONE,
    PULSE,          // Slow pulse
    SWEEP,          // Color sweep
    BEACON,         // Periodic flash
    MORSE,          // Morse code
    STROBE,         // Fast strobe
    BREATHE         // Breathing effect
};

struct PatternConfig {
    VisualPattern pattern;
    uint16_t tempo_ms;
    uint8_t color_r;
    uint8_t color_g;
    uint8_t color_b;
    const char* morse_text;     // For MORSE pattern
};

// Start a visual pattern
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
               OpticalProfile& profile, uint8_t& rate_hz);

} // namespace modem_optical

#endif // MYCOBRAIN_MODEM_OPTICAL_H

