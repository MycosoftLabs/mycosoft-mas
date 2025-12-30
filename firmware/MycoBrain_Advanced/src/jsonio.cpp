/**
 * MycoBrain Advanced Firmware - JSON I/O Implementation
 */

#include "jsonio.h"

namespace jsonio {

// =============================================================================
// PRIVATE STATE
// =============================================================================
static OperatingMode currentMode = OperatingMode::HUMAN;
static bool debugEnabled = false;

// =============================================================================
// INITIALIZATION
// =============================================================================
void init() {
    currentMode = OperatingMode::HUMAN;
    debugEnabled = false;
}

// =============================================================================
// MODE MANAGEMENT
// =============================================================================
void setMode(OperatingMode mode) {
    currentMode = mode;
}

OperatingMode getMode() {
    return currentMode;
}

bool isMachineMode() {
    return currentMode == OperatingMode::MACHINE;
}

// =============================================================================
// NDJSON OUTPUT
// =============================================================================

void emitAck(const char* command, const char* message) {
    StaticJsonDocument<256> doc;
    doc["type"] = "ack";
    doc["cmd"] = command;
    if (message) {
        doc["msg"] = message;
    }
    doc["ok"] = true;
    serializeJson(doc, Serial);
    Serial.println();
}

void emitError(const char* command, const char* error) {
    StaticJsonDocument<256> doc;
    doc["type"] = "err";
    doc["cmd"] = command;
    doc["error"] = error;
    doc["ok"] = false;
    serializeJson(doc, Serial);
    Serial.println();
}

void emitTelemetry(JsonDocument& doc) {
    doc["type"] = "telemetry";
    serializeJson(doc, Serial);
    Serial.println();
}

void emitPeripheral(JsonDocument& doc) {
    doc["type"] = "periph";
    serializeJson(doc, Serial);
    Serial.println();
}

void emitStatus(JsonDocument& doc) {
    doc["type"] = "status";
    serializeJson(doc, Serial);
    Serial.println();
}

void emitJson(JsonDocument& doc) {
    serializeJson(doc, Serial);
    Serial.println();
}

void emitRawJson(const char* json) {
    Serial.println(json);
}

// =============================================================================
// HUMAN-MODE OUTPUT
// =============================================================================

void printBanner(const char* text) {
    if (currentMode == OperatingMode::HUMAN) {
        Serial.println(text);
    }
}

void printHelp(const char* text) {
    if (currentMode == OperatingMode::HUMAN) {
        Serial.println(text);
    }
}

void printInfo(const char* text) {
    if (currentMode == OperatingMode::HUMAN) {
        Serial.println(text);
    }
}

void printDebug(const char* text) {
    if (currentMode == OperatingMode::HUMAN && debugEnabled) {
        Serial.print("[DBG] ");
        Serial.println(text);
    }
}

// =============================================================================
// DEBUG MODE
// =============================================================================
void setDebug(bool enabled) {
    debugEnabled = enabled;
}

bool isDebugEnabled() {
    return debugEnabled;
}

// =============================================================================
// CRC16 UTILITIES (CCITT)
// =============================================================================

uint16_t crc16Update(uint16_t crc, uint8_t data) {
    crc ^= (uint16_t)data << 8;
    for (int i = 0; i < 8; i++) {
        if (crc & 0x8000) {
            crc = (crc << 1) ^ CRC16_POLY;
        } else {
            crc <<= 1;
        }
    }
    return crc;
}

uint16_t crc16(const uint8_t* data, size_t length) {
    uint16_t crc = CRC16_INIT;
    for (size_t i = 0; i < length; i++) {
        crc = crc16Update(crc, data[i]);
    }
    return crc;
}

// =============================================================================
// BASE64 UTILITIES
// =============================================================================

static const char base64Chars[] = 
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static int base64CharToVal(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '+') return 62;
    if (c == '/') return 63;
    return -1;
}

size_t base64Decode(const char* input, uint8_t* output, size_t maxOutputLen) {
    size_t inputLen = strlen(input);
    size_t outputLen = 0;
    
    uint32_t buffer = 0;
    int bits = 0;
    
    for (size_t i = 0; i < inputLen && outputLen < maxOutputLen; i++) {
        char c = input[i];
        if (c == '=') break;
        
        int val = base64CharToVal(c);
        if (val < 0) continue;
        
        buffer = (buffer << 6) | val;
        bits += 6;
        
        if (bits >= 8) {
            bits -= 8;
            output[outputLen++] = (buffer >> bits) & 0xFF;
        }
    }
    
    return outputLen;
}

size_t base64Encode(const uint8_t* input, size_t inputLen, char* output, size_t maxOutputLen) {
    size_t outputLen = 0;
    
    for (size_t i = 0; i < inputLen && outputLen + 4 < maxOutputLen; i += 3) {
        uint32_t n = ((uint32_t)input[i]) << 16;
        if (i + 1 < inputLen) n |= ((uint32_t)input[i + 1]) << 8;
        if (i + 2 < inputLen) n |= input[i + 2];
        
        output[outputLen++] = base64Chars[(n >> 18) & 0x3F];
        output[outputLen++] = base64Chars[(n >> 12) & 0x3F];
        output[outputLen++] = (i + 1 < inputLen) ? base64Chars[(n >> 6) & 0x3F] : '=';
        output[outputLen++] = (i + 2 < inputLen) ? base64Chars[n & 0x3F] : '=';
    }
    
    output[outputLen] = '\0';
    return outputLen;
}

} // namespace jsonio

