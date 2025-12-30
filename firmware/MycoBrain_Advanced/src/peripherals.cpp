/**
 * MycoBrain Advanced Firmware - Peripheral Discovery Implementation
 */

#include "peripherals.h"
#include "jsonio.h"
#include <Wire.h>

namespace peripherals {

// =============================================================================
// CONSTANTS
// =============================================================================
#define MAX_PERIPHERALS 16
#define KNOWN_DEVICES_COUNT 12

// =============================================================================
// KNOWN I2C DEVICE DATABASE
// =============================================================================
struct KnownDevice {
    uint8_t address;
    PeripheralType type;
    const char* vendor;
    const char* product;
};

static const KnownDevice knownDevices[] = {
    {0x76, PeripheralType::BME688, "Bosch", "BME688"},
    {0x77, PeripheralType::BME688, "Bosch", "BME688-ALT"},
    {0x44, PeripheralType::SHT4X, "Sensirion", "SHT40"},
    {0x45, PeripheralType::SHT4X, "Sensirion", "SHT45"},
    {0x23, PeripheralType::BH1750, "ROHM", "BH1750"},
    {0x5C, PeripheralType::BH1750, "ROHM", "BH1750-ALT"},
    {0x29, PeripheralType::VL53L0X, "ST", "VL53L0X"},
    {0x3C, PeripheralType::UNKNOWN, "Generic", "OLED-128x64"},
    {0x3D, PeripheralType::UNKNOWN, "Generic", "OLED-128x64-ALT"},
    {0x50, PeripheralType::EEPROM_ID, "Generic", "EEPROM-ID"},
    {0x51, PeripheralType::EEPROM_ID, "Generic", "EEPROM-ID"},
    {0x68, PeripheralType::UNKNOWN, "InvenSense", "MPU6050"}
};

// =============================================================================
// STATE
// =============================================================================
static Peripheral peripheralList[MAX_PERIPHERALS];
static size_t peripheralCount = 0;
static bool hotplugEnabled = false;
static uint32_t lastScanTime = 0;
static char boardMac[18] = "00:00:00:00:00:00";

// =============================================================================
// INITIALIZATION
// =============================================================================
void init() {
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.setClock(100000);  // 100kHz I2C
    
    // Get board MAC address for device UID
    uint64_t mac = ESP.getEfuseMac();
    snprintf(boardMac, sizeof(boardMac), "%02X:%02X:%02X:%02X:%02X:%02X",
             (uint8_t)(mac >> 40), (uint8_t)(mac >> 32),
             (uint8_t)(mac >> 24), (uint8_t)(mac >> 16),
             (uint8_t)(mac >> 8), (uint8_t)mac);
    
    peripheralCount = 0;
    hotplugEnabled = false;
    
    // Initial scan
    scan();
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

const char* getTypeName(PeripheralType type) {
    switch (type) {
        case PeripheralType::MIC: return "mic";
        case PeripheralType::LIDAR: return "lidar";
        case PeripheralType::PIXEL_ARRAY: return "pixel_array";
        case PeripheralType::CAMERA_PROXY: return "camera_proxy";
        case PeripheralType::PHOTODIODE_RX: return "photodiode_rx";
        case PeripheralType::FAST_LED_TX: return "fast_led_tx";
        case PeripheralType::VIBRATOR: return "vibrator";
        case PeripheralType::BME688: return "bme688";
        case PeripheralType::SHT4X: return "sht4x";
        case PeripheralType::BH1750: return "bh1750";
        case PeripheralType::VL53L0X: return "vl53l0x";
        case PeripheralType::EEPROM_ID: return "eeprom_id";
        default: return "unknown";
    }
}

PeripheralType identifyByAddress(uint8_t address) {
    for (size_t i = 0; i < KNOWN_DEVICES_COUNT; i++) {
        if (knownDevices[i].address == address) {
            return knownDevices[i].type;
        }
    }
    return PeripheralType::UNKNOWN;
}

static const KnownDevice* getKnownDevice(uint8_t address) {
    for (size_t i = 0; i < KNOWN_DEVICES_COUNT; i++) {
        if (knownDevices[i].address == address) {
            return &knownDevices[i];
        }
    }
    return nullptr;
}

// =============================================================================
// SCANNING
// =============================================================================

void scan() {
    // Mark all as offline first
    for (size_t i = 0; i < peripheralCount; i++) {
        peripheralList[i].online = false;
    }
    
    // Scan I2C bus
    for (uint8_t addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        uint8_t error = Wire.endTransmission();
        
        if (error == 0) {
            // Device found
            bool exists = false;
            size_t existingIdx = 0;
            
            // Check if already in list
            for (size_t i = 0; i < peripheralCount; i++) {
                if (peripheralList[i].address == addr) {
                    peripheralList[i].online = true;
                    peripheralList[i].last_seen = millis();
                    exists = true;
                    existingIdx = i;
                    break;
                }
            }
            
            // Add new device
            if (!exists && peripheralCount < MAX_PERIPHERALS) {
                Peripheral* p = &peripheralList[peripheralCount];
                p->address = addr;
                p->type = identifyByAddress(addr);
                p->online = true;
                p->last_seen = millis();
                
                // Generate UID
                snprintf(p->uid, sizeof(p->uid), "i2c-%s-0x%02X", boardMac, addr);
                
                // Fill in known device info
                const KnownDevice* known = getKnownDevice(addr);
                if (known) {
                    strncpy(p->vendor, known->vendor, sizeof(p->vendor) - 1);
                    strncpy(p->product, known->product, sizeof(p->product) - 1);
                } else {
                    strncpy(p->vendor, "Unknown", sizeof(p->vendor) - 1);
                    snprintf(p->product, sizeof(p->product), "Device@0x%02X", addr);
                }
                strncpy(p->revision, "1.0", sizeof(p->revision) - 1);
                
                peripheralCount++;
            }
        }
    }
    
    lastScanTime = millis();
}

size_t getCount() {
    return peripheralCount;
}

const Peripheral* getPeripheral(size_t index) {
    if (index < peripheralCount) {
        return &peripheralList[index];
    }
    return nullptr;
}

const Peripheral* getPeripheralByAddress(uint8_t address) {
    for (size_t i = 0; i < peripheralCount; i++) {
        if (peripheralList[i].address == address) {
            return &peripheralList[i];
        }
    }
    return nullptr;
}

// =============================================================================
// DESCRIPTOR GENERATION
// =============================================================================

void generateDescriptor(const Peripheral* periph, JsonDocument& doc) {
    doc["type"] = "periph";
    doc["board_id"] = boardMac;
    doc["bus"] = "i2c0";
    
    char addrStr[8];
    snprintf(addrStr, sizeof(addrStr), "0x%02X", periph->address);
    doc["address"] = addrStr;
    
    doc["peripheral_uid"] = periph->uid;
    doc["peripheral_type"] = getTypeName(periph->type);
    doc["vendor"] = periph->vendor;
    doc["product"] = periph->product;
    doc["revision"] = periph->revision;
    doc["online"] = periph->online;
    
    // Add capabilities based on type
    JsonArray caps = doc["capabilities"].to<JsonArray>();
    
    switch (periph->type) {
        case PeripheralType::BME688:
            caps.add("telemetry");
            caps.add("gas_sensing");
            doc["data_plane"]["control"] = "i2c";
            doc["data_plane"]["stream"] = "none";
            doc["ui_widget"] = "environmental_sensor";
            break;
            
        case PeripheralType::SHT4X:
            caps.add("telemetry");
            doc["data_plane"]["control"] = "i2c";
            doc["ui_widget"] = "temp_humidity_sensor";
            break;
            
        case PeripheralType::VL53L0X:
            caps.add("telemetry");
            caps.add("distance_sensing");
            doc["data_plane"]["control"] = "i2c";
            doc["ui_widget"] = "distance_sensor";
            break;
            
        case PeripheralType::PIXEL_ARRAY:
            caps.add("control");
            caps.add("optical_tx");
            doc["data_plane"]["control"] = "gpio";
            doc["ui_widget"] = "led_strip";
            break;
            
        case PeripheralType::MIC:
            caps.add("acoustic_rx");
            doc["data_plane"]["stream"] = "i2s";
            doc["ui_widget"] = "audio_input";
            break;
            
        default:
            caps.add("telemetry");
            doc["ui_widget"] = "generic_device";
            break;
    }
}

void generateDescriptorList(JsonDocument& doc) {
    doc["type"] = "periph_list";
    doc["board_id"] = boardMac;
    doc["count"] = peripheralCount;
    
    JsonArray list = doc["peripherals"].to<JsonArray>();
    for (size_t i = 0; i < peripheralCount; i++) {
        JsonObject item = list.add<JsonObject>();
        item["address"] = peripheralList[i].address;
        item["uid"] = peripheralList[i].uid;
        item["type"] = getTypeName(peripheralList[i].type);
        item["product"] = peripheralList[i].product;
        item["online"] = peripheralList[i].online;
    }
}

// =============================================================================
// HOTPLUG
// =============================================================================

void setHotplug(bool enabled) {
    hotplugEnabled = enabled;
}

bool isHotplugEnabled() {
    return hotplugEnabled;
}

// =============================================================================
// DECLARED PERIPHERALS
// =============================================================================

bool declarePeripheral(PeripheralType type, const char* uid, 
                       uint8_t pin, uint16_t count) {
    if (peripheralCount >= MAX_PERIPHERALS) {
        return false;
    }
    
    Peripheral* p = &peripheralList[peripheralCount];
    p->address = 0xFF;  // Special address for declared peripherals
    p->type = type;
    p->online = true;
    p->last_seen = millis();
    
    strncpy(p->uid, uid, sizeof(p->uid) - 1);
    strncpy(p->vendor, "Declared", sizeof(p->vendor) - 1);
    snprintf(p->product, sizeof(p->product), "%s@GPIO%d", getTypeName(type), pin);
    strncpy(p->revision, "1.0", sizeof(p->revision) - 1);
    
    peripheralCount++;
    return true;
}

bool undeclarePeripheral(const char* uid) {
    for (size_t i = 0; i < peripheralCount; i++) {
        if (strcmp(peripheralList[i].uid, uid) == 0) {
            // Shift remaining peripherals
            for (size_t j = i; j < peripheralCount - 1; j++) {
                peripheralList[j] = peripheralList[j + 1];
            }
            peripheralCount--;
            return true;
        }
    }
    return false;
}

// =============================================================================
// UPDATE
// =============================================================================

void update() {
    if (hotplugEnabled) {
        if (millis() - lastScanTime >= I2C_SCAN_INTERVAL_MS) {
            scan();
        }
    }
}

} // namespace peripherals

