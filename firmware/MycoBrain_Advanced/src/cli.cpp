/**
 * MycoBrain Advanced Firmware - CLI Implementation
 */

#include "cli.h"
#include "jsonio.h"
#include "pixel.h"
#include "buzzer.h"
#include "modem_optical.h"
#include "modem_audio.h"
#include "peripherals.h"
#include "stimulus.h"
#include <ArduinoJson.h>

namespace cli {

// =============================================================================
// COMMAND BUFFER
// =============================================================================
static char cmdBuffer[CLI_BUFFER_SIZE];
static size_t cmdIndex = 0;

// =============================================================================
// COMMAND REGISTRY
// =============================================================================
#define MAX_COMMANDS 32

struct CommandEntry {
    const char* name;
    CommandHandler handler;
    const char* help;
};

static CommandEntry commands[MAX_COMMANDS];
static size_t commandCount = 0;

// =============================================================================
// COMMAND HANDLERS
// =============================================================================

static void cmdHelp(int argc, const char* argv[]) {
    if (jsonio::isMachineMode()) {
        StaticJsonDocument<1024> doc;
        doc["type"] = "help";
        JsonArray cmds = doc["commands"].to<JsonArray>();
        for (size_t i = 0; i < commandCount; i++) {
            cmds.add(commands[i].name);
        }
        jsonio::emitJson(doc);
    } else {
        jsonio::printHelp("\n=== MycoBrain Advanced Commands ===\n");
        for (size_t i = 0; i < commandCount; i++) {
            Serial.print("  ");
            Serial.print(commands[i].name);
            if (commands[i].help) {
                Serial.print(" - ");
                Serial.print(commands[i].help);
            }
            Serial.println();
        }
        jsonio::printHelp("");
    }
}

static void cmdMode(int argc, const char* argv[]) {
    if (argc < 2) {
        if (jsonio::isMachineMode()) {
            jsonio::emitError("mode", "missing argument: human|machine");
        } else {
            jsonio::printInfo("Usage: mode human|machine");
        }
        return;
    }
    
    if (strcmp(argv[1], "machine") == 0) {
        jsonio::setMode(OperatingMode::MACHINE);
        jsonio::emitAck("mode", "machine mode enabled");
    } else if (strcmp(argv[1], "human") == 0) {
        jsonio::setMode(OperatingMode::HUMAN);
        jsonio::printInfo("Human mode enabled. Type 'help' for commands.");
    } else {
        if (jsonio::isMachineMode()) {
            jsonio::emitError("mode", "invalid mode");
        } else {
            jsonio::printInfo("Usage: mode human|machine");
        }
    }
}

static void cmdStatus(int argc, const char* argv[]) {
    StaticJsonDocument<1024> doc;
    
    // System info
    doc["firmware"] = FIRMWARE_NAME;
    doc["version"] = FIRMWARE_VERSION;
    doc["uptime_ms"] = millis();
    doc["mode"] = jsonio::isMachineMode() ? "machine" : "human";
    doc["debug"] = jsonio::isDebugEnabled();
    
    // LED status
    uint8_t r, g, b;
    bool ledOn;
    pixel::Pattern ledPattern;
    pixel::getStatus(r, g, b, ledOn, ledPattern);
    doc["led"]["r"] = r;
    doc["led"]["g"] = g;
    doc["led"]["b"] = b;
    doc["led"]["on"] = ledOn;
    
    // Buzzer status
    bool buzzerPlaying;
    buzzer::Pattern buzzerPattern;
    uint16_t buzzerFreq;
    buzzer::getStatus(buzzerPlaying, buzzerPattern, buzzerFreq);
    doc["buzzer"]["playing"] = buzzerPlaying;
    
    // Modem status
    bool optxActive, optxPattern;
    OpticalProfile optProfile;
    uint8_t optRate;
    modem_optical::getStatus(optxActive, optxPattern, optProfile, optRate);
    doc["optx"]["active"] = optxActive;
    doc["optx"]["pattern"] = optxPattern;
    
    bool aotxActive, aotxPattern;
    AcousticProfile aoProfile;
    uint16_t aoSymbol;
    modem_audio::getStatus(aotxActive, aotxPattern, aoProfile, aoSymbol);
    doc["aotx"]["active"] = aotxActive;
    doc["aotx"]["pattern"] = aotxPattern;
    
    // Peripheral count
    doc["peripherals"] = peripherals::getCount();
    
    jsonio::emitStatus(doc);
}

static void cmdDbg(int argc, const char* argv[]) {
    if (argc < 2) {
        bool enabled = jsonio::isDebugEnabled();
        if (jsonio::isMachineMode()) {
            StaticJsonDocument<128> doc;
            doc["type"] = "ack";
            doc["cmd"] = "dbg";
            doc["enabled"] = enabled;
            jsonio::emitJson(doc);
        } else {
            Serial.print("Debug: ");
            Serial.println(enabled ? "on" : "off");
        }
        return;
    }
    
    if (strcmp(argv[1], "on") == 0) {
        jsonio::setDebug(true);
        jsonio::emitAck("dbg", "debug enabled");
    } else if (strcmp(argv[1], "off") == 0) {
        jsonio::setDebug(false);
        jsonio::emitAck("dbg", "debug disabled");
    }
}

static void cmdLed(int argc, const char* argv[]) {
    if (argc < 2) {
        jsonio::emitError("led", "missing subcommand: rgb|off|status");
        return;
    }
    
    if (strcmp(argv[1], "rgb") == 0) {
        if (argc < 5) {
            jsonio::emitError("led", "usage: led rgb <r> <g> <b>");
            return;
        }
        uint8_t r = atoi(argv[2]);
        uint8_t g = atoi(argv[3]);
        uint8_t b = atoi(argv[4]);
        pixel::setRGB(r, g, b);
        
        StaticJsonDocument<128> doc;
        doc["type"] = "ack";
        doc["cmd"] = "led";
        doc["r"] = r;
        doc["g"] = g;
        doc["b"] = b;
        jsonio::emitJson(doc);
    } else if (strcmp(argv[1], "off") == 0) {
        pixel::off();
        jsonio::emitAck("led", "off");
    } else if (strcmp(argv[1], "status") == 0) {
        uint8_t r, g, b;
        bool on;
        pixel::Pattern pattern;
        pixel::getStatus(r, g, b, on, pattern);
        
        StaticJsonDocument<128> doc;
        doc["type"] = "status";
        doc["cmd"] = "led";
        doc["r"] = r;
        doc["g"] = g;
        doc["b"] = b;
        doc["on"] = on;
        jsonio::emitJson(doc);
    } else {
        jsonio::emitError("led", "unknown subcommand");
    }
}

static void cmdBuzz(int argc, const char* argv[]) {
    if (argc < 2) {
        jsonio::emitError("buzz", "missing subcommand: tone|pattern|stop");
        return;
    }
    
    if (strcmp(argv[1], "tone") == 0) {
        if (argc < 4) {
            jsonio::emitError("buzz", "usage: buzz tone <hz> <ms>");
            return;
        }
        uint16_t freq = atoi(argv[2]);
        uint16_t dur = atoi(argv[3]);
        buzzer::tone(freq, dur);
        jsonio::emitAck("buzz", "tone played");
    } else if (strcmp(argv[1], "pattern") == 0) {
        if (argc < 3) {
            jsonio::emitError("buzz", "usage: buzz pattern <name>");
            return;
        }
        
        buzzer::Pattern pattern = buzzer::Pattern::NONE;
        if (strcmp(argv[2], "coin") == 0) pattern = buzzer::Pattern::COIN;
        else if (strcmp(argv[2], "bump") == 0) pattern = buzzer::Pattern::BUMP;
        else if (strcmp(argv[2], "power") == 0) pattern = buzzer::Pattern::POWER;
        else if (strcmp(argv[2], "1up") == 0) pattern = buzzer::Pattern::ONE_UP;
        else if (strcmp(argv[2], "morgio") == 0) pattern = buzzer::Pattern::MORGIO;
        else if (strcmp(argv[2], "alert") == 0) pattern = buzzer::Pattern::ALERT;
        else if (strcmp(argv[2], "warning") == 0) pattern = buzzer::Pattern::WARNING;
        else if (strcmp(argv[2], "success") == 0) pattern = buzzer::Pattern::SUCCESS;
        else if (strcmp(argv[2], "error") == 0) pattern = buzzer::Pattern::ERROR_TONE;
        else {
            jsonio::emitError("buzz", "unknown pattern");
            return;
        }
        
        buzzer::startPattern(pattern);
        jsonio::emitAck("buzz", argv[2]);
    } else if (strcmp(argv[1], "stop") == 0) {
        buzzer::stopPattern();
        buzzer::stop();
        jsonio::emitAck("buzz", "stopped");
    } else {
        jsonio::emitError("buzz", "unknown subcommand");
    }
}

static void cmdOptx(int argc, const char* argv[]) {
    if (argc < 2) {
        jsonio::emitError("optx", "missing subcommand: start|stop|pattern|status");
        return;
    }
    
    if (strcmp(argv[1], "stop") == 0) {
        modem_optical::stopTx();
        modem_optical::stopPattern();
        jsonio::emitAck("optx", "stopped");
    } else if (strcmp(argv[1], "status") == 0) {
        bool txActive, patternActive;
        OpticalProfile profile;
        uint8_t rate;
        modem_optical::getStatus(txActive, patternActive, profile, rate);
        
        StaticJsonDocument<256> doc;
        doc["type"] = "status";
        doc["cmd"] = "optx";
        doc["tx_active"] = txActive;
        doc["pattern_active"] = patternActive;
        doc["rate_hz"] = rate;
        jsonio::emitJson(doc);
    } else if (strcmp(argv[1], "start") == 0) {
        // Parse JSON config from remaining args
        jsonio::emitAck("optx", "use JSON format for start command");
    } else if (strcmp(argv[1], "pattern") == 0) {
        if (argc < 3) {
            jsonio::emitError("optx", "usage: optx pattern <name>");
            return;
        }
        
        modem_optical::PatternConfig config;
        config.tempo_ms = 500;
        config.color_r = 255;
        config.color_g = 255;
        config.color_b = 255;
        
        if (strcmp(argv[2], "pulse") == 0) {
            config.pattern = modem_optical::VisualPattern::PULSE;
        } else if (strcmp(argv[2], "sweep") == 0) {
            config.pattern = modem_optical::VisualPattern::SWEEP;
        } else if (strcmp(argv[2], "beacon") == 0) {
            config.pattern = modem_optical::VisualPattern::BEACON;
        } else if (strcmp(argv[2], "strobe") == 0) {
            config.pattern = modem_optical::VisualPattern::STROBE;
            config.tempo_ms = 100;
        } else {
            jsonio::emitError("optx", "unknown pattern");
            return;
        }
        
        modem_optical::startPattern(config);
        jsonio::emitAck("optx", argv[2]);
    }
}

static void cmdAotx(int argc, const char* argv[]) {
    if (argc < 2) {
        jsonio::emitError("aotx", "missing subcommand: start|stop|pattern|status");
        return;
    }
    
    if (strcmp(argv[1], "stop") == 0) {
        modem_audio::stopTx();
        modem_audio::stopPattern();
        jsonio::emitAck("aotx", "stopped");
    } else if (strcmp(argv[1], "status") == 0) {
        bool txActive, patternActive;
        AcousticProfile profile;
        uint16_t symbolMs;
        modem_audio::getStatus(txActive, patternActive, profile, symbolMs);
        
        StaticJsonDocument<256> doc;
        doc["type"] = "status";
        doc["cmd"] = "aotx";
        doc["tx_active"] = txActive;
        doc["pattern_active"] = patternActive;
        doc["symbol_ms"] = symbolMs;
        jsonio::emitJson(doc);
    } else if (strcmp(argv[1], "pattern") == 0) {
        if (argc < 3) {
            jsonio::emitError("aotx", "usage: aotx pattern <name>");
            return;
        }
        
        modem_audio::PatternConfig config;
        config.freq_start = 1000;
        config.freq_end = 2000;
        config.duration_ms = 1000;
        config.tempo_ms = 200;
        config.repeat = true;
        
        if (strcmp(argv[2], "sweep") == 0) {
            config.pattern = modem_audio::AudioPattern::SWEEP;
        } else if (strcmp(argv[2], "chirp") == 0) {
            config.pattern = modem_audio::AudioPattern::CHIRP;
        } else if (strcmp(argv[2], "pulse") == 0) {
            config.pattern = modem_audio::AudioPattern::PULSE_TRAIN;
        } else if (strcmp(argv[2], "siren") == 0) {
            config.pattern = modem_audio::AudioPattern::SIREN;
        } else {
            jsonio::emitError("aotx", "unknown pattern");
            return;
        }
        
        modem_audio::startPattern(config);
        jsonio::emitAck("aotx", argv[2]);
    }
}

static void cmdPeriph(int argc, const char* argv[]) {
    if (argc < 2) {
        jsonio::emitError("periph", "missing subcommand: scan|list|describe|hotplug");
        return;
    }
    
    if (strcmp(argv[1], "scan") == 0) {
        peripherals::scan();
        jsonio::emitAck("periph", "scan complete");
    } else if (strcmp(argv[1], "list") == 0) {
        StaticJsonDocument<1024> doc;
        peripherals::generateDescriptorList(doc);
        jsonio::emitJson(doc);
    } else if (strcmp(argv[1], "describe") == 0) {
        if (argc < 3) {
            jsonio::emitError("periph", "usage: periph describe <uid>");
            return;
        }
        
        // Find peripheral by UID
        size_t count = peripherals::getCount();
        for (size_t i = 0; i < count; i++) {
            const peripherals::Peripheral* p = peripherals::getPeripheral(i);
            if (p && strcmp(p->uid, argv[2]) == 0) {
                StaticJsonDocument<512> doc;
                peripherals::generateDescriptor(p, doc);
                jsonio::emitJson(doc);
                return;
            }
        }
        jsonio::emitError("periph", "peripheral not found");
    } else if (strcmp(argv[1], "hotplug") == 0) {
        if (argc < 3) {
            bool enabled = peripherals::isHotplugEnabled();
            StaticJsonDocument<128> doc;
            doc["type"] = "ack";
            doc["cmd"] = "periph";
            doc["hotplug"] = enabled;
            jsonio::emitJson(doc);
        } else if (strcmp(argv[2], "on") == 0) {
            peripherals::setHotplug(true);
            jsonio::emitAck("periph", "hotplug enabled");
        } else if (strcmp(argv[2], "off") == 0) {
            peripherals::setHotplug(false);
            jsonio::emitAck("periph", "hotplug disabled");
        }
    }
}

static void cmdOut(int argc, const char* argv[]) {
    if (argc < 3) {
        jsonio::emitError("out", "usage: out set <1|2|3> <0|1>");
        return;
    }
    
    if (strcmp(argv[1], "set") == 0) {
        int channel = atoi(argv[2]);
        int value = atoi(argv[3]);
        
        int pin = -1;
        if (channel == 1) pin = PIN_OUT_1;
        else if (channel == 2) pin = PIN_OUT_2;
        else if (channel == 3) pin = PIN_OUT_3;
        
        if (pin < 0) {
            jsonio::emitError("out", "invalid channel");
            return;
        }
        
        pinMode(pin, OUTPUT);
        digitalWrite(pin, value ? HIGH : LOW);
        
        StaticJsonDocument<128> doc;
        doc["type"] = "ack";
        doc["cmd"] = "out";
        doc["channel"] = channel;
        doc["value"] = value;
        jsonio::emitJson(doc);
    }
}

static void cmdStim(int argc, const char* argv[]) {
    if (argc < 2) {
        jsonio::emitError("stim", "missing subcommand: light|sound|stop|status");
        return;
    }
    
    if (strcmp(argv[1], "stop") == 0) {
        stimulus::stopAll();
        jsonio::emitAck("stim", "stopped");
    } else if (strcmp(argv[1], "status") == 0) {
        bool lightActive, soundActive;
        uint32_t elapsed;
        uint16_t cycles;
        stimulus::getStatus(lightActive, soundActive, elapsed, cycles);
        
        StaticJsonDocument<256> doc;
        doc["type"] = "status";
        doc["cmd"] = "stim";
        doc["light_active"] = lightActive;
        doc["sound_active"] = soundActive;
        doc["elapsed_ms"] = elapsed;
        doc["cycles"] = cycles;
        jsonio::emitJson(doc);
    } else {
        jsonio::emitAck("stim", "use JSON format for complex stimulus config");
    }
}

// =============================================================================
// JSON COMMAND PARSING
// =============================================================================
static void parseJsonCommand(const char* json) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, json);
    
    if (error) {
        jsonio::emitError("json", "parse error");
        return;
    }
    
    const char* cmd = doc["cmd"];
    if (!cmd) {
        jsonio::emitError("json", "missing cmd field");
        return;
    }
    
    // Route to appropriate handler
    if (strcmp(cmd, "led.rgb") == 0 || strcmp(cmd, "led rgb") == 0) {
        uint8_t r = doc["r"] | 0;
        uint8_t g = doc["g"] | 0;
        uint8_t b = doc["b"] | 0;
        pixel::setRGB(r, g, b);
        jsonio::emitAck("led.rgb", "ok");
    } else if (strcmp(cmd, "led.off") == 0) {
        pixel::off();
        jsonio::emitAck("led.off", "ok");
    } else if (strcmp(cmd, "buzz.tone") == 0) {
        uint16_t freq = doc["hz"] | 1000;
        uint16_t dur = doc["ms"] | 100;
        buzzer::tone(freq, dur);
        jsonio::emitAck("buzz.tone", "ok");
    } else if (strcmp(cmd, "buzz.pattern") == 0) {
        const char* name = doc["name"];
        if (name) {
            const char* args[] = {"buzz", "pattern", name};
            cmdBuzz(3, args);
        }
    } else if (strcmp(cmd, "optx.start") == 0) {
        modem_optical::TxConfig config;
        
        const char* profile = doc["profile"] | "camera_ook";
        if (strcmp(profile, "camera_ook") == 0) {
            config.profile = OpticalProfile::CAMERA_OOK;
        } else if (strcmp(profile, "camera_manchester") == 0) {
            config.profile = OpticalProfile::CAMERA_MANCHESTER;
        }
        
        config.rate_hz = doc["rate_hz"] | 10;
        config.repeat = doc["repeat"] | false;
        config.include_crc = doc["include_crc"] | true;
        config.color_r = doc["rgb"][0] | 255;
        config.color_g = doc["rgb"][1] | 255;
        config.color_b = doc["rgb"][2] | 255;
        
        // Decode base64 payload
        const char* payload_b64 = doc["payload_b64"];
        if (payload_b64) {
            static uint8_t payloadBuffer[PAYLOAD_MAX_SIZE];
            size_t len = jsonio::base64Decode(payload_b64, payloadBuffer, PAYLOAD_MAX_SIZE);
            config.payload = payloadBuffer;
            config.payload_len = len;
            
            modem_optical::startTx(config);
            jsonio::emitAck("optx.start", "transmitting");
        } else {
            jsonio::emitError("optx.start", "missing payload_b64");
        }
    } else if (strcmp(cmd, "aotx.start") == 0) {
        modem_audio::TxConfig config;
        
        const char* profile = doc["profile"] | "simple_fsk";
        if (strcmp(profile, "simple_fsk") == 0) {
            config.profile = AcousticProfile::SIMPLE_FSK;
        }
        
        config.symbol_ms = doc["symbol_ms"] | 30;
        config.freq_0 = doc["f0"] | 1800;
        config.freq_1 = doc["f1"] | 2400;
        config.repeat = doc["repeat"] | false;
        config.include_crc = doc["include_crc"] | true;
        config.preamble_freq = 1000;
        config.preamble_ms = doc["preamble_ms"] | 200;
        
        // Decode base64 payload
        const char* payload_b64 = doc["payload_b64"];
        if (payload_b64) {
            static uint8_t payloadBuffer[PAYLOAD_MAX_SIZE];
            size_t len = jsonio::base64Decode(payload_b64, payloadBuffer, PAYLOAD_MAX_SIZE);
            config.payload = payloadBuffer;
            config.payload_len = len;
            
            modem_audio::startTx(config);
            jsonio::emitAck("aotx.start", "transmitting");
        } else {
            jsonio::emitError("aotx.start", "missing payload_b64");
        }
    } else if (strcmp(cmd, "stim.light") == 0) {
        stimulus::LightStimulus config;
        config.color_r = doc["rgb"][0] | 255;
        config.color_g = doc["rgb"][1] | 255;
        config.color_b = doc["rgb"][2] | 255;
        config.on_ms = doc["on_ms"] | 500;
        config.off_ms = doc["off_ms"] | 500;
        config.ramp_ms = doc["ramp_ms"] | 0;
        config.repeat_count = doc["repeat"] | 0;
        config.delay_ms = doc["delay_ms"] | 0;
        
        stimulus::startLight(config);
        jsonio::emitAck("stim.light", "started");
    } else if (strcmp(cmd, "stim.sound") == 0) {
        stimulus::SoundStimulus config;
        config.frequency = doc["hz"] | 1000;
        config.on_ms = doc["on_ms"] | 200;
        config.off_ms = doc["off_ms"] | 200;
        config.freq_sweep_hz = doc["sweep_hz"] | 0;
        config.repeat_count = doc["repeat"] | 0;
        config.delay_ms = doc["delay_ms"] | 0;
        
        stimulus::startSound(config);
        jsonio::emitAck("stim.sound", "started");
    } else {
        jsonio::emitError("json", "unknown command");
    }
}

// =============================================================================
// INITIALIZATION
// =============================================================================
void init() {
    cmdIndex = 0;
    commandCount = 0;
    
    // Register built-in commands
    registerCommand("help", cmdHelp, "Show available commands");
    registerCommand("mode", cmdMode, "Set mode: human|machine");
    registerCommand("status", cmdStatus, "Get system status");
    registerCommand("dbg", cmdDbg, "Debug mode: on|off");
    registerCommand("led", cmdLed, "LED control: rgb|off|status");
    registerCommand("buzz", cmdBuzz, "Buzzer: tone|pattern|stop");
    registerCommand("optx", cmdOptx, "Optical TX: start|stop|pattern|status");
    registerCommand("aotx", cmdAotx, "Audio TX: start|stop|pattern|status");
    registerCommand("periph", cmdPeriph, "Peripherals: scan|list|describe|hotplug");
    registerCommand("out", cmdOut, "Outputs: set <1|2|3> <0|1>");
    registerCommand("stim", cmdStim, "Stimulus: light|sound|stop|status");
    
    // Legacy aliases
    registerCommand("coin", [](int, const char**) { buzzer::startPattern(buzzer::Pattern::COIN); jsonio::emitAck("coin", "ok"); }, nullptr);
    registerCommand("morgio", [](int, const char**) { buzzer::startPattern(buzzer::Pattern::MORGIO); jsonio::emitAck("morgio", "ok"); }, nullptr);
}

void registerCommand(const char* name, CommandHandler handler, const char* help) {
    if (commandCount < MAX_COMMANDS) {
        commands[commandCount].name = name;
        commands[commandCount].handler = handler;
        commands[commandCount].help = help;
        commandCount++;
    }
}

// =============================================================================
// COMMAND PARSING
// =============================================================================
void executeCommand(const char* line) {
    // Skip empty lines
    if (line[0] == '\0') return;
    
    // Check if JSON command
    if (line[0] == '{') {
        parseJsonCommand(line);
        return;
    }
    
    // Parse as space-delimited tokens
    static const char* argv[16];
    static char lineCopy[CLI_BUFFER_SIZE];
    strncpy(lineCopy, line, CLI_BUFFER_SIZE - 1);
    
    int argc = 0;
    char* token = strtok(lineCopy, " \t");
    while (token && argc < 16) {
        argv[argc++] = token;
        token = strtok(nullptr, " \t");
    }
    
    if (argc == 0) return;
    
    // Find and execute command
    for (size_t i = 0; i < commandCount; i++) {
        if (strcmp(argv[0], commands[i].name) == 0) {
            commands[i].handler(argc, argv);
            return;
        }
    }
    
    // Unknown command
    if (jsonio::isMachineMode()) {
        jsonio::emitError(argv[0], "unknown command");
    } else {
        Serial.print("Unknown command: ");
        Serial.println(argv[0]);
        Serial.println("Type 'help' for available commands.");
    }
}

// =============================================================================
// MAIN UPDATE LOOP
// =============================================================================
void update() {
    while (Serial.available()) {
        char c = Serial.read();
        
        if (c == '\n' || c == '\r') {
            if (cmdIndex > 0) {
                cmdBuffer[cmdIndex] = '\0';
                executeCommand(cmdBuffer);
                cmdIndex = 0;
            }
        } else if (cmdIndex < CLI_BUFFER_SIZE - 1) {
            cmdBuffer[cmdIndex++] = c;
        }
    }
}

void printHelp() {
    cmdHelp(0, nullptr);
}

} // namespace cli

