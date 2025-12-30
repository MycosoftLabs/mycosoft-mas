/**
 * MycoBrain Advanced Firmware - Configuration
 * 
 * Hardware pin definitions and system constants for the MycoBrain ESP32-S3 board.
 * DO NOT modify pin assignments unless you have verified the hardware schematic.
 * 
 * @author Mycosoft
 * @version 2.0.0
 */

#ifndef MYCOBRAIN_CONFIG_H
#define MYCOBRAIN_CONFIG_H

// =============================================================================
// VERSION INFO
// =============================================================================
#define FIRMWARE_NAME       "MycoBrain-Advanced"
#define FIRMWARE_VERSION    "2.0.0"
#define FIRMWARE_BUILD_DATE __DATE__

// =============================================================================
// HARDWARE PIN DEFINITIONS - SIDE A (THIS FIRMWARE TARGET)
// =============================================================================

// Onboard NeoPixel LED (SK6805 / WS2812-class, NOT PWM RGB!)
// Net: NEO_1 → series resistor → D7 SK6805 DI
#define PIN_NEOPIXEL        15
#define NEOPIXEL_COUNT      1

// Buzzer (MOSFET-driven piezo)
#define PIN_BUZZER          16

// I2C Bus (3.3V with pullups)
#define PIN_I2C_SCL         4
#define PIN_I2C_SDA         5

// Digital Outputs - MOSFET channels (NOT LEDs!)
// These control external loads via MOSFET switches
#define PIN_OUT_1           12
#define PIN_OUT_2           13
#define PIN_OUT_3           14

// Analog Inputs
#define PIN_AIN_1           6
#define PIN_AIN_2           7
#define PIN_AIN_3           10
#define PIN_AIN_4           11

// =============================================================================
// SERIAL CONFIGURATION
// =============================================================================
#define SERIAL_BAUD         115200
#define SERIAL_TIMEOUT_MS   100

// =============================================================================
// OPERATING MODES
// =============================================================================
enum class OperatingMode {
    HUMAN,      // Verbose output, help text, banners allowed
    MACHINE     // NDJSON only, no ASCII art, strict protocol
};

// =============================================================================
// MODEM PROFILES
// =============================================================================

// Optical TX profiles
enum class OpticalProfile {
    CAMERA_OOK,         // Simple On-Off Keying for cameras (5-20 Hz)
    CAMERA_MANCHESTER,  // Manchester encoding for better sync
    SPATIAL_SM,         // Spatial modulation (requires >1 LED)
    PATTERN_ONLY        // Non-data patterns (pulse, sweep, beacon)
};

// Acoustic TX profiles
enum class AcousticProfile {
    SIMPLE_FSK,     // 2-tone FSK with preamble + CRC16
    GGWAVE_LIKE,    // Multi-tone encoding (future)
    PATTERN_ONLY    // Non-data patterns (chirp, sweep, morse)
};

// =============================================================================
// PERIPHERAL TYPES
// =============================================================================
enum class PeripheralType {
    UNKNOWN,
    MIC,
    LIDAR,
    PIXEL_ARRAY,
    CAMERA_PROXY,
    PHOTODIODE_RX,
    FAST_LED_TX,
    VIBRATOR,
    BME688,
    SHT4X,
    BH1750,
    VL53L0X,
    EEPROM_ID
};

// =============================================================================
// TIMING CONSTANTS
// =============================================================================
#define TELEMETRY_INTERVAL_MS   1000
#define I2C_SCAN_INTERVAL_MS    5000
#define SCHEDULER_TICK_MS       1

// =============================================================================
// BUFFER SIZES
// =============================================================================
#define CLI_BUFFER_SIZE         512
#define JSON_DOC_SIZE           2048
#define PAYLOAD_MAX_SIZE        256

// =============================================================================
// CRC16 POLYNOMIAL (CCITT)
// =============================================================================
#define CRC16_POLY              0x1021
#define CRC16_INIT              0xFFFF

#endif // MYCOBRAIN_CONFIG_H

