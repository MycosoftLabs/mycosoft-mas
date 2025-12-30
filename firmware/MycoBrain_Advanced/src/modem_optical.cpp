/**
 * MycoBrain Advanced Firmware - Optical Modem Implementation
 * 
 * LiFi-style data transmission via NeoPixel LED.
 */

#include "modem_optical.h"
#include "pixel.h"
#include "jsonio.h"

namespace modem_optical {

// =============================================================================
// STATE
// =============================================================================
static bool txActive = false;
static TxConfig txConfig;
static uint8_t* txPayload = nullptr;
static size_t txPayloadLen = 0;
static size_t txByteIndex = 0;
static uint8_t txBitIndex = 0;
static uint32_t lastSymbolTime = 0;
static uint16_t symbolPeriod_ms = 100;  // Default 10 Hz
static bool manchesterPhase = false;
static uint16_t crcValue = 0;
static bool crcOk = true;

static bool patternActive = false;
static PatternConfig patternConfig;
static uint32_t patternStartTime = 0;

// =============================================================================
// INITIALIZATION
// =============================================================================
void init() {
    txActive = false;
    patternActive = false;
    txPayload = nullptr;
}

// =============================================================================
// OOK ENCODING
// Bit 1 = LED on, Bit 0 = LED off
// =============================================================================
static void transmitOOK() {
    if (txByteIndex >= txPayloadLen) {
        if (txConfig.repeat) {
            txByteIndex = 0;
            txBitIndex = 0;
        } else {
            stopTx();
            return;
        }
    }
    
    uint8_t currentByte = txPayload[txByteIndex];
    bool bit = (currentByte >> (7 - txBitIndex)) & 0x01;
    
    if (bit) {
        pixel::setRGB(txConfig.color_r, txConfig.color_g, txConfig.color_b);
    } else {
        pixel::off();
    }
    
    txBitIndex++;
    if (txBitIndex >= 8) {
        txBitIndex = 0;
        txByteIndex++;
    }
}

// =============================================================================
// MANCHESTER ENCODING
// Bit 1 = low-to-high transition, Bit 0 = high-to-low transition
// =============================================================================
static void transmitManchester() {
    if (txByteIndex >= txPayloadLen) {
        if (txConfig.repeat) {
            txByteIndex = 0;
            txBitIndex = 0;
            manchesterPhase = false;
        } else {
            stopTx();
            return;
        }
    }
    
    uint8_t currentByte = txPayload[txByteIndex];
    bool bit = (currentByte >> (7 - txBitIndex)) & 0x01;
    
    // Manchester: each bit takes 2 symbol periods
    if (bit) {
        // Bit 1: low then high
        if (!manchesterPhase) {
            pixel::off();
        } else {
            pixel::setRGB(txConfig.color_r, txConfig.color_g, txConfig.color_b);
        }
    } else {
        // Bit 0: high then low
        if (!manchesterPhase) {
            pixel::setRGB(txConfig.color_r, txConfig.color_g, txConfig.color_b);
        } else {
            pixel::off();
        }
    }
    
    manchesterPhase = !manchesterPhase;
    if (!manchesterPhase) {
        txBitIndex++;
        if (txBitIndex >= 8) {
            txBitIndex = 0;
            txByteIndex++;
        }
    }
}

// =============================================================================
// TRANSMISSION CONTROL
// =============================================================================

bool startTx(const TxConfig& config) {
    if (txActive) {
        stopTx();
    }
    
    // Copy config
    txConfig = config;
    
    // Allocate payload buffer (with optional CRC)
    size_t totalLen = config.payload_len;
    if (config.include_crc) {
        totalLen += 2;  // 16-bit CRC
    }
    
    txPayload = (uint8_t*)malloc(totalLen);
    if (!txPayload) {
        return false;
    }
    
    // Copy payload
    memcpy(txPayload, config.payload, config.payload_len);
    
    // Calculate and append CRC if requested
    if (config.include_crc) {
        crcValue = jsonio::crc16(config.payload, config.payload_len);
        txPayload[config.payload_len] = (crcValue >> 8) & 0xFF;
        txPayload[config.payload_len + 1] = crcValue & 0xFF;
        crcOk = true;
    }
    
    txPayloadLen = totalLen;
    txByteIndex = 0;
    txBitIndex = 0;
    manchesterPhase = false;
    
    // Calculate symbol period from rate
    if (config.rate_hz > 0) {
        symbolPeriod_ms = 1000 / config.rate_hz;
    } else {
        symbolPeriod_ms = 100;  // Default 10 Hz
    }
    
    // For Manchester, we need half the period per phase
    if (config.profile == OpticalProfile::CAMERA_MANCHESTER) {
        symbolPeriod_ms /= 2;
    }
    
    lastSymbolTime = millis();
    txActive = true;
    
    return true;
}

void stopTx() {
    txActive = false;
    pixel::off();
    
    if (txPayload) {
        free(txPayload);
        txPayload = nullptr;
    }
}

bool isTxActive() {
    return txActive;
}

void getTxStatus(bool& active, size_t& bytes_sent, size_t& total_bytes,
                 uint8_t& current_bit, bool& crc_ok) {
    active = txActive;
    bytes_sent = txByteIndex;
    total_bytes = txPayloadLen;
    current_bit = txBitIndex;
    crc_ok = crcOk;
}

// =============================================================================
// PATTERN MODE
// =============================================================================

void startPattern(const PatternConfig& config) {
    patternConfig = config;
    patternActive = true;
    patternStartTime = millis();
    
    // Map to pixel patterns
    pixel::Pattern pxPattern = pixel::Pattern::NONE;
    switch (config.pattern) {
        case VisualPattern::PULSE:
            pxPattern = pixel::Pattern::PULSE;
            break;
        case VisualPattern::SWEEP:
            pxPattern = pixel::Pattern::SWEEP;
            break;
        case VisualPattern::BEACON:
            pxPattern = pixel::Pattern::BEACON;
            break;
        case VisualPattern::STROBE:
            pxPattern = pixel::Pattern::BLINK;
            break;
        case VisualPattern::BREATHE:
            pxPattern = pixel::Pattern::PULSE;
            break;
        default:
            break;
    }
    
    pixel::startPattern(pxPattern, config.tempo_ms, 
                       config.color_r, config.color_g, config.color_b);
}

void stopPattern() {
    patternActive = false;
    pixel::stopPattern();
}

bool isPatternActive() {
    return patternActive;
}

// =============================================================================
// UPDATE (call from main loop)
// =============================================================================
void update() {
    // Handle data transmission
    if (txActive) {
        uint32_t now = millis();
        if (now - lastSymbolTime >= symbolPeriod_ms) {
            lastSymbolTime = now;
            
            switch (txConfig.profile) {
                case OpticalProfile::CAMERA_OOK:
                    transmitOOK();
                    break;
                case OpticalProfile::CAMERA_MANCHESTER:
                    transmitManchester();
                    break;
                default:
                    break;
            }
        }
    }
    
    // Pattern mode is handled by pixel::update()
}

// =============================================================================
// STATUS
// =============================================================================
void getStatus(bool& tx_active, bool& pattern_active,
               OpticalProfile& profile, uint8_t& rate_hz) {
    tx_active = txActive;
    pattern_active = patternActive;
    profile = txConfig.profile;
    rate_hz = txConfig.rate_hz;
}

} // namespace modem_optical

