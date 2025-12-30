/**
 * MycoBrain Advanced Firmware - Peripheral Discovery Module
 * 
 * I2C peripheral manager with automatic discovery and descriptor reporting.
 * Enables plug-and-play widget generation on the dashboard.
 * 
 * Features:
 * - I2C bus scanning
 * - Device identification (known I2C addresses)
 * - Descriptor generation (JSON schema for dashboard)
 * - Hotplug detection
 * 
 * @author Mycosoft
 * @version 2.0.0
 */

#ifndef MYCOBRAIN_PERIPHERALS_H
#define MYCOBRAIN_PERIPHERALS_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include "config.h"

namespace peripherals {

// =============================================================================
// INITIALIZATION
// =============================================================================
void init();

// =============================================================================
// PERIPHERAL DESCRIPTOR
// =============================================================================

struct Peripheral {
    uint8_t address;            // I2C address
    PeripheralType type;        // Device type
    char uid[32];               // Unique identifier
    char vendor[32];
    char product[32];
    char revision[16];
    bool online;                // Currently detected
    uint32_t last_seen;         // Timestamp
};

// =============================================================================
// SCANNING AND DISCOVERY
// =============================================================================

// Scan I2C bus and update peripheral list
void scan();

// Get number of detected peripherals
size_t getCount();

// Get peripheral by index
const Peripheral* getPeripheral(size_t index);

// Get peripheral by address
const Peripheral* getPeripheralByAddress(uint8_t address);

// =============================================================================
// DESCRIPTOR GENERATION
// =============================================================================

// Generate JSON descriptor for a peripheral
void generateDescriptor(const Peripheral* periph, JsonDocument& doc);

// Generate descriptor list for all peripherals
void generateDescriptorList(JsonDocument& doc);

// =============================================================================
// HOTPLUG
// =============================================================================

// Enable/disable hotplug detection
void setHotplug(bool enabled);

// Check if hotplug is enabled
bool isHotplugEnabled();

// =============================================================================
// DECLARED PERIPHERALS
// For devices that can't be auto-discovered (e.g., NeoPixel arrays)
// =============================================================================

// Declare a peripheral manually
bool declarePeripheral(PeripheralType type, const char* uid, 
                       uint8_t pin = 0, uint16_t count = 0);

// Remove a declared peripheral
bool undeclarePeripheral(const char* uid);

// =============================================================================
// SCHEDULER TICK
// Call from main loop for hotplug detection
// =============================================================================
void update();

// =============================================================================
// KNOWN DEVICE DATABASE
// =============================================================================

// Get type name as string
const char* getTypeName(PeripheralType type);

// Identify device type by I2C address
PeripheralType identifyByAddress(uint8_t address);

} // namespace peripherals

#endif // MYCOBRAIN_PERIPHERALS_H

