# MYCA Hybrid Voice-Brain Architecture Implementation
## February 3, 2026

> **📌 UPDATED**: This document remains valid for brain architecture. Additional memory integration added February 5, 2026:
> - **[MYCA_MEMORY_BRAIN_INTEGRATION_FEB05_2026.md](./MYCA_MEMORY_BRAIN_INTEGRATION_FEB05_2026.md)** - Memory-Brain integration
> - **[MEMORY_SYSTEM_COMPLETE_FEB05_2026.md](./MEMORY_SYSTEM_COMPLETE_FEB05_2026.md)** - Complete system reference

---

This document summarizes the implementation of the MYCA Hybrid Voice-Brain Architecture.

## Overview

The architecture makes MYCA the central "brain" with PersonaPlex/Moshi serving as voice I/O only.

### Components Created

#### Phase 1: MYCA Brain Router
- **File**: `mycosoft_mas/llm/frontier_router.py`
- Routes all questions through frontier LLMs (Gemini, Claude, GPT-4)
- Implements streaming responses
- Supports multi-LLM fallback

#### Phase 2: Frontier LLM Integration  
- **File**: `mycosoft_mas/llm/streaming_bridge.py`
- Handles streaming LLM tokens to PersonaPlex
- Buffers tokens into speakable chunks
- Converts to Moshi-compatible format (kind=2)

#### Phase 3: Voice-to-Brain Bridge
- **Modified**: `services/personaplex-local/personaplex_bridge_nvidia.py`
- Added `MYCA_BRAIN_ENABLED` config
- Added `call_myca_brain()` function
- Added `inject_brain_response()` function
- Routes user speech through brain before Moshi responds

#### Phase 4: MYCA Persona Roles
- **File**: `config/myca_full_persona.txt`
- 7,930 character comprehensive persona
- Defines 9 roles: Orchestrator, Memory Keeper, Lead Engineer, etc.
- Includes NatureOS device knowledge

#### Phase 5: Sub-Agent Personas
- **File**: `mycosoft_mas/personas/sub_agents.py`
- Defines user tiers (Morgan, Employee, Customer, Tool)
- Creates sub-agent personas (Research Assistant, Device Monitor, Support Agent)
- Implements SubAgentRouter for routing

#### Phase 6: UI Brain Visualization
- **Modified**: `website/app/test-voice/page.tsx`
- Added brain status state (idle/thinking/responding)
- Added brain response display
- Shows LLM provider being used

#### Phase 7: Tool Integration Pipeline
- **File**: `mycosoft_mas/llm/tool_pipeline.py`
- Implements ToolRegistry with 9 default tools
- ToolExecutor for executing tools
- ConversationToolManager for mid-conversation calls

### API Endpoints Created

| Endpoint | Description |
|----------|-------------|
| `POST /voice/brain/chat` | Non-streaming brain response |
| `POST /voice/brain/stream` | Streaming brain response (SSE) |
| `GET /voice/brain/status` | Brain status and providers |
| `GET /tools/list` | List available tools |
| `POST /tools/execute` | Execute a single tool |
| `POST /tools/execute/batch` | Execute multiple tools |
| `GET /tools/history` | Tool execution history |

### Architecture Flow

\\\
1. User speaks â†’ Moshi STT â†’ Text extracted
2. Text â†’ PersonaPlex Bridge â†’ MYCA Brain API
3. MYCA Brain â†’ Frontier LLM (Gemini/Claude/GPT-4)
4. Response â†’ Streaming Bridge â†’ Moshi TTS injection
5. Moshi speaks MYCA's response
\\\

### Tools Available

1. **calculator** - Mathematical expressions
2. **device_status** - NatureOS device readings
3. **mindex_query** - Fungal knowledge search
4. **memory_recall** - Memory system queries
5. **execute_workflow** - n8n automation
6. **agent_invoke** - Specialized agents
7. **code_execute** - Sandboxed code execution
8. **search_documents** - Documentation search
9. **weather** - Weather information

### Configuration

Environment variables:
- `MYCA_BRAIN_ENABLED=true` - Enable brain routing
- `GEMINI_API_KEY` - Gemini API key
- `ANTHROPIC_API_KEY` - Claude API key
- `OPENAI_API_KEY` - OpenAI API key

### Testing

Test at: **http://localhost:3010/test-voice**

The brain status panel shows:
- Thinking state (yellow pulse)
- Responding state (green pulse)
- Brain response preview
- LLM provider used

### Next Steps

1. Deploy to MAS VM (192.168.0.188)
2. Test with live PersonaPlex connection
3. Fine-tune response streaming latency
4. Add more tool implementations
5. Implement memory persistence
