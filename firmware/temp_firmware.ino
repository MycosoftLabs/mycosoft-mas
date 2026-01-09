/*
 * MycoBrain Side-A - Dual Mode Firmware with BSEC2 Smell Detection
 * 
 * This firmware accepts BOTH:
 *   - CLI commands: "status", "help", "scan", "smell", etc.
 *   - JSON commands: {"cmd":"status"}, {"type":"cmd","op":"status"}, etc.
 * 
 * BSEC2 Integration:
 *   - Uses Bosch BSEC2 library for IAQ, eCO2, bVOC, and gas classification
 *   - Falls back to Adafruit BME680 if BSEC2 fails to initialize
 *   - Gas classification enables smell detection (trained patterns)
 * 
 * Arduino IDE Settings:
 *   - USB CDC on boot: Enabled
 *   - USB Mode: Hardware CDC and JTAG
 *   - PSRAM: OPI PSRAM
 *   - CPU Frequency: 240 MHz
 *   - Flash Mode: QIO @ 80 MHz
 *   - Flash Size: 16 MB
 *   - Partition Scheme: 16MB Flash, 3MB App / 9.9MB FATFS
 *   - Upload Speed: 921600
 */

#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>
#include <Adafruit_BME680.h>

// Try to include BSEC2 if available
#define USE_BSEC2 1

#if USE_BSEC2
#include "bsec2.h"
#include "bsec_selectivity.h"
#endif

#include "soc/rtc_cntl_reg.h"

#ifndef ARRAY_LEN
  #define ARRAY_LEN(x) (sizeof(x) / sizeof((x)[0]))
#endif
