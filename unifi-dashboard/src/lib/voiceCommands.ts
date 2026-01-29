"use client";

/**
 * Voice Command Handler for MYCA
 * Parses voice commands and dispatches actions to appropriate handlers
 */

export interface VoiceCommand {
  type: 'map' | 'data' | 'agent' | 'device' | 'search' | 'navigation' | 'general';
  action: string;
  params: Record<string, any>;
  confidence: number;
  rawText: string;
}

export interface MapCommand {
  action: 'zoom_in' | 'zoom_out' | 'pan' | 'center' | 'show_layer' | 'hide_layer' | 'filter' | 'highlight';
  location?: { lat: number; lng: number };
  zoomLevel?: number;
  layerName?: string;
  filterType?: string;
  deviceId?: string;
}

// Command patterns for different types
const COMMAND_PATTERNS = {
  map: {
    zoom_in: /\b(zoom in|zoom closer|magnify|enlarge)\b/i,
    zoom_out: /\b(zoom out|zoom away|shrink|smaller)\b/i,
    pan: /\b(pan to|move to|go to|navigate to)\s+(.+)/i,
    center: /\b(center on|focus on|show me)\s+(.+)/i,
    show_layer: /\b(show|enable|turn on|display)\s+(layer|overlay)?\s*(.+)/i,
    hide_layer: /\b(hide|disable|turn off|remove)\s+(layer|overlay)?\s*(.+)/i,
    filter: /\b(filter|show only|display only)\s+(.+)/i,
    highlight: /\b(highlight|mark|point out)\s+(.+)/i,
  },
  data: {
    query: /\b(what|how many|show|list|find|search for)\s+(.+)/i,
    status: /\b(status|state|health)\s+(?:of\s+)?(.+)/i,
    count: /\b(count|number of|how many)\s+(.+)/i,
  },
  agent: {
    start: /\b(start|run|execute|launch)\s+(?:the\s+)?(.+?)\s*agent\b/i,
    stop: /\b(stop|halt|kill|terminate)\s+(?:the\s+)?(.+?)\s*agent\b/i,
    status: /\b(?:agent|agents?)\s+status\b/i,
    list: /\b(list|show)\s+(?:all\s+)?agents\b/i,
  },
  device: {
    control: /\b(turn on|turn off|activate|deactivate)\s+(.+)/i,
    status: /\b(check|what is|status of)\s+(.+)\s+device\b/i,
    locate: /\b(find|locate|where is)\s+(.+)\s+device\b/i,
  },
  navigation: {
    go: /\b(go to|open|show|navigate to)\s+(dashboard|topology|agents?|devices?|settings?|security)\b/i,
  },
};

// Location aliases for common places
const LOCATION_ALIASES: Record<string, { lat: number; lng: number }> = {
  'san francisco': { lat: 37.7749, lng: -122.4194 },
  'new york': { lat: 40.7128, lng: -74.0060 },
  'los angeles': { lat: 34.0522, lng: -118.2437 },
  'seattle': { lat: 47.6062, lng: -122.3321 },
  'chicago': { lat: 41.8781, lng: -87.6298 },
  'headquarters': { lat: 37.7749, lng: -122.4194 },
  'home': { lat: 37.7749, lng: -122.4194 },
};

/**
 * Parse voice command text into structured command
 */
export function parseVoiceCommand(text: string): VoiceCommand | null {
  const normalizedText = text.toLowerCase().trim();
  
  // Check map commands
  for (const [action, pattern] of Object.entries(COMMAND_PATTERNS.map)) {
    const match = normalizedText.match(pattern);
    if (match) {
      return {
        type: 'map',
        action,
        params: extractParams(action, match),
        confidence: 0.9,
        rawText: text,
      };
    }
  }
  
  // Check data commands
  for (const [action, pattern] of Object.entries(COMMAND_PATTERNS.data)) {
    const match = normalizedText.match(pattern);
    if (match) {
      return {
        type: 'data',
        action,
        params: { query: match[2] || match[1] },
        confidence: 0.85,
        rawText: text,
      };
    }
  }
  
  // Check agent commands
  for (const [action, pattern] of Object.entries(COMMAND_PATTERNS.agent)) {
    const match = normalizedText.match(pattern);
    if (match) {
      return {
        type: 'agent',
        action,
        params: { agentName: match[2] || match[1] },
        confidence: 0.9,
        rawText: text,
      };
    }
  }
  
  // Check device commands
  for (const [action, pattern] of Object.entries(COMMAND_PATTERNS.device)) {
    const match = normalizedText.match(pattern);
    if (match) {
      return {
        type: 'device',
        action,
        params: { deviceName: match[2] || match[1] },
        confidence: 0.85,
        rawText: text,
      };
    }
  }
  
  // Check navigation commands
  for (const [action, pattern] of Object.entries(COMMAND_PATTERNS.navigation)) {
    const match = normalizedText.match(pattern);
    if (match) {
      return {
        type: 'navigation',
        action,
        params: { destination: match[2] },
        confidence: 0.95,
        rawText: text,
      };
    }
  }
  
  // General command (fallback)
  return {
    type: 'general',
    action: 'chat',
    params: { message: text },
    confidence: 0.5,
    rawText: text,
  };
}

/**
 * Extract parameters from command match
 */
function extractParams(action: string, match: RegExpMatchArray): Record<string, any> {
  const params: Record<string, any> = {};
  
  if (action === 'pan' || action === 'center') {
    const locationText = match[2]?.toLowerCase();
    if (locationText) {
      // Check for known locations
      for (const [name, coords] of Object.entries(LOCATION_ALIASES)) {
        if (locationText.includes(name)) {
          params.location = coords;
          break;
        }
      }
      // Check for coordinates (e.g., "37.7, -122.4")
      const coordMatch = locationText.match(/(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)/);
      if (coordMatch) {
        params.location = { lat: parseFloat(coordMatch[1]), lng: parseFloat(coordMatch[2]) };
      }
      params.locationText = locationText;
    }
  }
  
  if (action === 'show_layer' || action === 'hide_layer') {
    params.layerName = match[3]?.trim() || match[2]?.trim();
  }
  
  if (action === 'filter') {
    params.filterQuery = match[2]?.trim();
  }
  
  if (action === 'highlight') {
    params.target = match[2]?.trim();
  }
  
  return params;
}

/**
 * Voice command dispatcher - sends commands to appropriate handlers
 */
export class VoiceCommandDispatcher {
  private handlers: Map<string, (command: VoiceCommand) => Promise<string>> = new Map();
  
  registerHandler(type: string, handler: (command: VoiceCommand) => Promise<string>) {
    this.handlers.set(type, handler);
  }
  
  async dispatch(command: VoiceCommand): Promise<string> {
    const handler = this.handlers.get(command.type);
    if (handler) {
      return handler(command);
    }
    return \I understood that as a \ command, but I don't have a handler for it yet.\;
  }
}

// Global dispatcher instance
let dispatcher: VoiceCommandDispatcher | null = null;

export function getVoiceCommandDispatcher(): VoiceCommandDispatcher {
  if (!dispatcher) {
    dispatcher = new VoiceCommandDispatcher();
    
    // Register default handlers
    dispatcher.registerHandler('map', async (cmd) => {
      return \Map command: \ with params \\;
    });
    
    dispatcher.registerHandler('data', async (cmd) => {
      return \Data query: \\;
    });
    
    dispatcher.registerHandler('agent', async (cmd) => {
      return \Agent command: \ \\;
    });
    
    dispatcher.registerHandler('device', async (cmd) => {
      return \Device command: \ \\;
    });
    
    dispatcher.registerHandler('navigation', async (cmd) => {
      return \Navigating to \\;
    });
    
    dispatcher.registerHandler('general', async (cmd) => {
      return \Processing: \\;
    });
  }
  return dispatcher;
}
