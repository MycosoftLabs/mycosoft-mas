/**
 * MycoBrain Advanced Firmware - Acoustic Modem Implementation
 * 
 * FSK-based data transmission via buzzer for microphone receivers.
 */

#include "modem_audio.h"
#include "buzzer.h"
#include "jsonio.h"

namespace modem_audio {

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
static bool inPreamble = false;
static uint32_t preambleEndTime = 0;
static uint16_t crcValue = 0;
static bool crcOk = true;

static bool patternActive = false;
static PatternConfig patternConfig;
static uint32_t patternStartTime = 0;
static uint16_t sweepFreq = 0;

// =============================================================================
// FSK PREAMBLE
// 8 alternating symbols to allow receiver synchronization
// =============================================================================
static const uint8_t FSK_PREAMBLE[] = {0xAA, 0xAA};  // 10101010 pattern

// =============================================================================
// INITIALIZATION
// =============================================================================
void init() {
    txActive = false;
    patternActive = false;
    txPayload = nullptr;
}

// =============================================================================
// FSK TRANSMISSION
// Bit 1 = freq_1 (high tone), Bit 0 = freq_0 (low tone)
// =============================================================================
static void transmitFSK() {
    // Handle preamble first
    if (inPreamble) {
        if (millis() >= preambleEndTime) {
            inPreamble = false;
            txByteIndex = 0;
            txBitIndex = 0;
        } else {
            // Alternate between f0 and f1 during preamble
            uint32_t elapsed = millis() - (preambleEndTime - txConfig.preamble_ms);
            bool high = ((elapsed / txConfig.symbol_ms) % 2) == 1;
            buzzer::tone(high ? txConfig.freq_1 : txConfig.freq_0, 0);
            return;
        }
    }
    
    if (txByteIndex >= txPayloadLen) {
        if (txConfig.repeat) {
            // Restart with preamble
            inPreamble = true;
            preambleEndTime = millis() + txConfig.preamble_ms;
            txByteIndex = 0;
            txBitIndex = 0;
        } else {
            stopTx();
            return;
        }
    }
    
    uint8_t currentByte = txPayload[txByteIndex];
    bool bit = (currentByte >> (7 - txBitIndex)) & 0x01;
    
    // Output appropriate frequency
    buzzer::tone(bit ? txConfig.freq_1 : txConfig.freq_0, 0);
    
    txBitIndex++;
    if (txBitIndex >= 8) {
        txBitIndex = 0;
        txByteIndex++;
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
    
    // Start with preamble
    if (config.preamble_ms > 0) {
        inPreamble = true;
        preambleEndTime = millis() + config.preamble_ms;
    } else {
        inPreamble = false;
    }
    
    lastSymbolTime = millis();
    txActive = true;
    
    return true;
}

void stopTx() {
    txActive = false;
    buzzer::stop();
    
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
    sweepFreq = config.freq_start;
}

void stopPattern() {
    patternActive = false;
    buzzer::stop();
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
        if (now - lastSymbolTime >= txConfig.symbol_ms) {
            lastSymbolTime = now;
            transmitFSK();
        }
    }
    
    // Handle pattern mode
    if (patternActive) {
        uint32_t elapsed = millis() - patternStartTime;
        
        switch (patternConfig.pattern) {
            case AudioPattern::SWEEP: {
                // Linear frequency sweep
                if (elapsed < patternConfig.duration_ms) {
                    float progress = (float)elapsed / patternConfig.duration_ms;
                    uint16_t freq = patternConfig.freq_start + 
                        (uint16_t)(progress * (patternConfig.freq_end - patternConfig.freq_start));
                    buzzer::tone(freq, 0);
                } else {
                    if (patternConfig.repeat) {
                        patternStartTime = millis();
                    } else {
                        stopPattern();
                    }
                }
                break;
            }
            
            case AudioPattern::CHIRP: {
                // Exponential frequency sweep (chirp)
                if (elapsed < patternConfig.duration_ms) {
                    float progress = (float)elapsed / patternConfig.duration_ms;
                    // Logarithmic sweep
                    float logStart = log((float)patternConfig.freq_start);
                    float logEnd = log((float)patternConfig.freq_end);
                    uint16_t freq = (uint16_t)exp(logStart + progress * (logEnd - logStart));
                    buzzer::tone(freq, 0);
                } else {
                    if (patternConfig.repeat) {
                        patternStartTime = millis();
                    } else {
                        stopPattern();
                    }
                }
                break;
            }
            
            case AudioPattern::PULSE_TRAIN: {
                // Pulsed tone
                uint32_t cyclePos = elapsed % (patternConfig.tempo_ms * 2);
                if (cyclePos < patternConfig.tempo_ms) {
                    buzzer::tone(patternConfig.freq_start, 0);
                } else {
                    buzzer::stop();
                }
                break;
            }
            
            case AudioPattern::SIREN: {
                // Alternating between two frequencies
                uint32_t cyclePos = elapsed % (patternConfig.tempo_ms * 2);
                if (cyclePos < patternConfig.tempo_ms) {
                    buzzer::tone(patternConfig.freq_start, 0);
                } else {
                    buzzer::tone(patternConfig.freq_end, 0);
                }
                break;
            }
            
            default:
                break;
        }
    }
}

// =============================================================================
// STATUS
// =============================================================================
void getStatus(bool& tx_active, bool& pattern_active,
               AcousticProfile& profile, uint16_t& symbol_ms) {
    tx_active = txActive;
    pattern_active = patternActive;
    profile = txConfig.profile;
    symbol_ms = txConfig.symbol_ms;
}

} // namespace modem_audio

