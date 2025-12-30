/**
 * MycoBrain Advanced Firmware - JSON I/O Module
 * 
 * NDJSON emission and JSON parsing helpers for machine-mode communication.
 * All output in machine mode MUST go through this module.
 * 
 * @author Mycosoft
 * @version 2.0.0
 */

#ifndef MYCOBRAIN_JSONIO_H
#define MYCOBRAIN_JSONIO_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include "config.h"

namespace jsonio {

// =============================================================================
// INITIALIZATION
// =============================================================================
void init();

// =============================================================================
// MODE MANAGEMENT
// =============================================================================
void setMode(OperatingMode mode);
OperatingMode getMode();
bool isMachineMode();

// =============================================================================
// NDJSON OUTPUT FUNCTIONS
// All emit a single JSON object per line (NDJSON format)
// =============================================================================

// Acknowledgment response
void emitAck(const char* command, const char* message = nullptr);

// Error response
void emitError(const char* command, const char* error);

// Telemetry data
void emitTelemetry(JsonDocument& doc);

// Peripheral descriptor
void emitPeripheral(JsonDocument& doc);

// Status response
void emitStatus(JsonDocument& doc);

// Generic JSON object
void emitJson(JsonDocument& doc);

// Raw JSON string (must be valid JSON)
void emitRawJson(const char* json);

// =============================================================================
// HUMAN-MODE OUTPUT (only works in HUMAN mode)
// =============================================================================

// Print banner/ASCII art (human mode only)
void printBanner(const char* text);

// Print help text (human mode only)
void printHelp(const char* text);

// Print info message (human mode only)
void printInfo(const char* text);

// Debug output (only if debug enabled AND human mode)
void printDebug(const char* text);

// =============================================================================
// DEBUG MODE
// =============================================================================
void setDebug(bool enabled);
bool isDebugEnabled();

// =============================================================================
// CRC16 UTILITIES
// =============================================================================
uint16_t crc16(const uint8_t* data, size_t length);
uint16_t crc16Update(uint16_t crc, uint8_t data);

// =============================================================================
// BASE64 UTILITIES
// =============================================================================
size_t base64Decode(const char* input, uint8_t* output, size_t maxOutputLen);
size_t base64Encode(const uint8_t* input, size_t inputLen, char* output, size_t maxOutputLen);

} // namespace jsonio

#endif // MYCOBRAIN_JSONIO_H

