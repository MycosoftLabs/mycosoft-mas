/**
 * MycoBrain Advanced Firmware - CLI Module
 * 
 * Line-based command parser supporting both plaintext and JSON commands.
 * - If line starts with '{', parse as JSON command
 * - Otherwise parse as space-delimited tokens
 * 
 * @author Mycosoft
 * @version 2.0.0
 */

#ifndef MYCOBRAIN_CLI_H
#define MYCOBRAIN_CLI_H

#include <Arduino.h>
#include "config.h"

namespace cli {

// =============================================================================
// INITIALIZATION
// =============================================================================
void init();

// =============================================================================
// MAIN LOOP FUNCTION
// Call this from loop() to process incoming serial data
// =============================================================================
void update();

// =============================================================================
// COMMAND REGISTRATION
// Commands are registered with a handler function
// =============================================================================
typedef void (*CommandHandler)(int argc, const char* argv[]);

// Register a command with its handler
void registerCommand(const char* name, CommandHandler handler, const char* help = nullptr);

// =============================================================================
// INTERNAL HELPERS (exposed for module use)
// =============================================================================

// Parse and execute a command line
void executeCommand(const char* line);

// Get the full command list (for help)
void printHelp();

} // namespace cli

#endif // MYCOBRAIN_CLI_H

