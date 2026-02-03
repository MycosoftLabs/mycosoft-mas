# PersonaPlex Architecture v2.0 - February 3, 2026

## Executive Summary

This document describes the refactored PersonaPlex voice integration architecture implementing strict separation of concerns. The key architectural principle is:

**MYCA Orchestrator is the ONLY component that makes decisions.**

All business logic (memory persistence, n8n workflow execution, agent routing, safety confirmation) is centralized in the Voice Orchestrator API. Client-side hooks and the PersonaPlex server handle only I/O operations.

---

## Part 1: Architecture Overview

### Previous Architecture (BROKEN)

```
Browser Hook → PersonaPlex (audio)
           → Memory API (direct)
           → n8n API (direct)
           → MAS Orchestrator (direct)
```

**Problems:**
- Multiple decision points
- Divergent behavior between interfaces
- Memory writes from multiple sources
- No centralized logging

### New Architecture (CORRECT)

```
Browser Hook → PersonaPlex (audio only)
           → Voice Orchestrator API (text/intent)
                    ↓
              [SINGLE BRAIN]
                    ↓
              Memory API (auto-save)
              n8n Workflows (triggered by orchestrator)
              MAS Agents (routed by orchestrator)
```

**Benefits:**
- Single decision path
- Consistent behavior across all interfaces
- Automatic memory persistence
- Action transparency in responses
- Future-proof for CLI, API, autonomous agents

---

## Part 2: Components Changed

### 2.1 usePersonaPlex Hook (Website)

**File:** `hooks/usePersonaPlex.ts`

**Removed:**
- `processWithMAS()` - Direct MAS API calls
- `saveToMemory()` - Direct memory API calls
- `recallFromMemory()` - Direct memory API calls
- `executeN8nWorkflow()` - Direct n8n API calls

**Added:**
- `sendToOrchestrator(transcript: string)` - Single entry point

**Interface:**
```typescript
interface UsePersonaPlexReturn {
  // Connection
  connect: () => Promise<void>
  disconnect: () => void
  status: ConnectionStatus
  
  // Audio
  micLevel: number
  agentLevel: number
  stats: AudioStats
  
  // Text
  transcript: string
  lastResponse: OrchestratorResponse | null
  
  // Single entry point
  sendToOrchestrator: (message: string) => Promise<OrchestratorResponse>
  conversationId: string
}
```

### 2.2 Voice Orchestrator API (Website)

**File:** `app/api/mas/voice/orchestrator/route.ts`

**Enhanced:**
- Automatic memory persistence (every turn saved)
- Structured response with actions taken
- Latency tracking
- Voice session context

**Response Interface:**
```typescript
interface VoiceOrchestratorResponse {
  conversation_id: string
  response_text: string
  audio_base64?: string
  
  // Action transparency
  actions: {
    memory_saved: boolean
    workflow_executed?: string
    agent_routed?: string
    confirmation_required?: boolean
  }
  
  // Telemetry
  latency_ms: number
  rtf?: number
}
```

### 2.3 Memory API (Website)

**File:** `app/api/memory/route.ts`

**Changes:**
- Added scope/namespace support
- Safer deletion (requires explicit scope + namespace_id)
- Separate summarization action

**Scopes:**
- `conversation` - Voice conversation turns
- `agent` - Agent-specific memory
- `system` - System-wide configuration
- `user` - User preferences

**Deletion Safety:**
```bash
# Old (DANGEROUS)
DELETE /api/memory?type=voice_session

# New (SAFE)
DELETE /api/memory?scope=conversation&namespace_id=conv_123&key=turn_1&confirm=true
```

---

## Part 3: New Components Created

### 3.1 WebSocket Protocol v1

**File:** `lib/voice/personaplex-protocol.ts`

Defines versioned WebSocket communication:

**Handshake:**
```typescript
{
  type: "hello",
  protocol: "personaplex-ws",
  version: "1.0.0",
  capabilities: { audio_in, audio_out, text_stream, stats },
  session: { conversation_id, persona_id, voice_prompt_hash }
}
```

**Message Types:**
- `audio_in` / `audio_out` - Opus audio
- `agent_text_partial` / `agent_text_final` - Transcript streaming
- `stats` - Latency, buffer, RTF metrics

**Version Mismatch:** Hard disconnect (no silent degradation)

### 3.2 RTF Watchdog

**File:** `lib/voice/rtf-watchdog.ts`

Monitors Real-Time Factor (RTF) for audio generation:

```
RTF = generation_time_ms / audio_duration_ms
```

**Thresholds:**
| RTF | Status | Action |
|-----|--------|--------|
| < 0.7 | Healthy | None |
| 0.7-0.9 | Warning | Yellow indicator |
| > 0.9 (2s) | Impending failure | Reduce chunk size |
| > 1.0 (3s) | Guaranteed stutter | Pause output, resync |

**UI Integration:** VoiceMonitorDashboard shows real-time RTF indicator

### 3.3 Voice Prompt Security

**File:** `lib/voice/voice-prompt-security.ts`
**Config:** `config/voice_prompt_whitelist.json`

**Policy:**
1. All voice prompts must be hashed (SHA-256)
2. Only whitelisted hashes accepted at runtime
3. Role-based access control
4. Audit logging for every session

**Whitelist Entry:**
```json
{
  "NATURAL_F2": {
    "hash": "sha256:9c1f...",
    "allowed_roles": ["myca_superadmin", "myca_admin", "myca_user"],
    "cloning": false
  }
}
```

### 3.4 Voice Session Topology Nodes

**File:** `components/mas/topology/agent-registry.ts`

Ephemeral voice session nodes appear in MAS topology:

```typescript
interface VoiceSessionNode {
  id: string                // "voice_session:conv_123"
  type: "voice_session"
  lifetime: "ephemeral"
  transport: "personaplex" | "elevenlabs" | "web-speech"
  rtf: number
  latencyMs: number
  invokedAgents: string[]
}
```

**Topology Edges:**
```
user → voice_session → myca-orchestrator
voice_session → [invoked_agents...]
```

---

## Part 4: PersonaPlex Bridge Security

**File:** `services/personaplex-local/personaplex_bridge_nvidia.py`

**Added:**
- `load_voice_prompt_whitelist()` - Load from config
- `validate_voice_prompt(prompt_name, user_role)` - Validate against whitelist

**Behavior:**
- Unknown prompts rejected (if `reject_unknown_hashes=true`)
- Role validation for restricted prompts
- All access logged for audit

---

## Part 5: File Summary

### Website Repository

| File | Action | Purpose |
|------|--------|---------|
| `hooks/usePersonaPlex.ts` | MODIFIED | Single orchestrator path |
| `app/api/mas/voice/orchestrator/route.ts` | MODIFIED | Auto-save memory, structured response |
| `app/api/memory/route.ts` | MODIFIED | Scope/namespace, safer deletion |
| `lib/voice/personaplex-protocol.ts` | CREATED | WebSocket protocol v1 |
| `lib/voice/rtf-watchdog.ts` | CREATED | RTF monitoring |
| `lib/voice/voice-prompt-security.ts` | CREATED | Voice prompt whitelist |
| `lib/voice/index.ts` | MODIFIED | Export new modules |
| `components/voice/VoiceMonitorDashboard.tsx` | MODIFIED | RTF indicator |
| `components/mas/topology/types.ts` | MODIFIED | voice_session node type |
| `components/mas/topology/agent-registry.ts` | MODIFIED | Voice session helpers |

### MAS Repository

| File | Action | Purpose |
|------|--------|---------|
| `services/personaplex-local/personaplex_bridge_nvidia.py` | MODIFIED | Voice prompt validation |
| `config/voice_prompt_whitelist.json` | CREATED | Voice prompt registry |

---

## Part 6: Integration Examples

### Using the Refactored Hook

```typescript
import { usePersonaPlex } from "@/hooks"

function VoiceInterface() {
  const { 
    connect, 
    disconnect, 
    sendToOrchestrator, 
    lastResponse 
  } = usePersonaPlex({
    serverUrl: "ws://localhost:8998/api/chat",
    voicePrompt: "NATURAL_F2",
  })
  
  // The hook only handles I/O
  // All business logic is in the orchestrator
  
  const handleSpeak = async (text: string) => {
    const response = await sendToOrchestrator(text)
    
    // Response includes what actions were taken
    console.log("Memory saved:", response.actions?.memory_saved)
    console.log("Agent routed:", response.actions?.agent_routed)
    console.log("Latency:", response.latency_ms, "ms")
  }
}
```

### Memory API with Scopes

```typescript
// Save to conversation scope
await fetch("/api/memory", {
  method: "POST",
  body: JSON.stringify({
    scope: "conversation",
    namespace_id: "conv_123",
    key: "turn_5",
    value: { input: "hello", output: "hi" },
    type: "voice_session",
  }),
})

// Safe deletion (requires confirm)
await fetch("/api/memory?scope=conversation&namespace_id=conv_123&confirm=true", {
  method: "DELETE",
})
```

---

## Part 7: Testing Checklist

- [ ] Hook only calls orchestrator (no direct MAS/memory/n8n)
- [ ] Orchestrator saves memory automatically on every turn
- [ ] Orchestrator returns structured response with actions
- [ ] WebSocket handshake validates protocol version
- [ ] RTF indicator shows in VoiceMonitorDashboard
- [ ] RTF status changes color based on threshold
- [ ] Unknown voice prompt hashes rejected
- [ ] Voice sessions appear in topology as ephemeral nodes
- [ ] Memory API requires scope for deletion
- [ ] Memory API rejects clear_all without confirmation

---

## Part 8: Migration Notes

### For Existing Code Using usePersonaPlex

**Before:**
```typescript
const { sendToMAS, saveToMemory, executeN8nWorkflow } = usePersonaPlex()

// Direct calls (WRONG)
await sendToMAS("hello")
await saveToMemory("key", value)
await executeN8nWorkflow("workflow")
```

**After:**
```typescript
const { sendToOrchestrator } = usePersonaPlex()

// Single entry point (CORRECT)
const response = await sendToOrchestrator("hello")
// Memory saved automatically
// Workflows triggered by orchestrator
// Actions reported in response.actions
```

### For Memory API Consumers

**Before:**
```typescript
DELETE /api/memory?type=voice_session  // DANGEROUS
```

**After:**
```typescript
DELETE /api/memory?scope=conversation&namespace_id=conv_123&confirm=true
```

---

## Conclusion

This architecture refactor ensures:

1. **Single Brain**: MYCA Orchestrator makes ALL decisions
2. **Consistent Behavior**: Same logic for voice, chat, API, CLI
3. **Automatic Persistence**: Memory saved without client action
4. **Action Transparency**: Clients know what happened
5. **Security**: Voice prompts validated, access logged
6. **Observability**: RTF monitoring, topology integration

The system is now ready for future expansion including:
- Multiple concurrent voice sessions
- Agent-to-agent voice interactions
- Autonomous agent self-talk
- Text chat interface reusing same orchestrator

---

*Document created: February 3, 2026*
*Architecture version: 2.0*
*Status: Implementation Complete*
