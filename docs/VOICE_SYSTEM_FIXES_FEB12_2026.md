# Voice System Fixes - February 12, 2026

## Summary

Fixed multiple issues with the PersonaPlex voice system that were causing incorrect AI identity, missing memory persistence, and wrong voice type.

## Issues Fixed

### 1. MYCA Persona Not Loading (persona_length: 111)

**Problem:** The PersonaPlex bridge was using a minimal fallback persona (111 chars) instead of the full MYCA identity, causing the AI to:
- Not know its name is MYCA
- Confuse Mycosoft with Microsoft
- Have generic personality instead of MYCA's defined character

**Fix:** Updated `config/myca_personaplex_short.txt` with comprehensive MYCA identity:
- Name: MYCA (pronounced MY-kah)
- Employer: MYCOSOFT (not Microsoft)
- Creator: Morgan, founder of Mycosoft
- Personality: Warm, confident, knowledgeable
- Role: Coordinates 227+ AI agents in the Multi-Agent System

**Result:** `persona_length: 1046` - Full persona now loaded

### 2. Voice Session Store Not Connected (voice_store_connected: false)

**Problem:** The VoiceSessionStore was failing to connect to the database, preventing:
- Session persistence
- Conversation history loading
- Memory bridge integration

**Root Causes Identified:**
1. Missing `memory` schema tables in MINDEX PostgreSQL
2. Wrong database credentials (was using VM SSH password instead of PostgreSQL password)
3. Missing Python path for `mycosoft_mas` module import

**Fixes Applied:**

#### a) Created Database Schema Migration
Created `MINDEX/mindex/migrations/0012_voice_session_store.sql` with:
- `memory.voice_sessions` - Session tracking
- `memory.voice_turns` - Conversation turns
- `memory.voice_tool_invocations` - Tool call logging
- `memory.voice_barge_in_events` - Interruption tracking
- `memory.end_voice_session()` - Stored function
- `memory.get_session_with_turns()` - Stored function
- `memory.voice_session_stats` - Statistics view

Applied via `scripts/_apply_voice_migration.py`

#### b) Fixed Database Credentials
Updated `services/personaplex-local/personaplex_bridge_nvidia.py`:
```python
# Wrong (VM SSH password):
os.environ["DATABASE_URL"] = "postgresql://mycosoft:REDACTED_VM_SSH_PASSWORD@192.168.0.189:5432/mindex"

# Correct (PostgreSQL password):
os.environ["DATABASE_URL"] = "postgresql://mycosoft:REDACTED_DB_PASSWORD@192.168.0.189:5432/mindex"
```

#### c) Fixed Python Path for Module Import
Added MAS repo to Python path at start of bridge:
```python
import sys
from pathlib import Path

MAS_REPO_PATH = Path(__file__).resolve().parent.parent.parent
if str(MAS_REPO_PATH) not in sys.path:
    sys.path.insert(0, str(MAS_REPO_PATH))
```

**Result:** `voice_store_connected: true`

### 3. Male Voice Instead of NATF2 Female Voice

**Problem:** User heard male voice instead of expected NATF2 female voice.

**Root Cause:** The Kyutai Moshi model (`kyutai/moshiko-pytorch-bf16`) does not include voice variety embeddings. The `start_personaplex.py` script sets `voice_prompt_dir` to an empty directory in the Kyutai model cache, so the requested `NATF2.pt` voice prompt file doesn't exist.

**Current Status:** Diagnosed but not yet fixed. Options:
1. Generate custom NATF2 embeddings from reference audio
2. Switch to NVIDIA Moshi model (has voice embeddings but different requirements)
3. Use a different TTS system for female voice

### 4. MAS Brain API Timeout

**Problem:** `/voice/brain/status` endpoint on MAS VM times out, preventing consciousness integration.

**Root Cause:** The `mycosoft_mas.llm.memory_brain` initialization is timing out, likely due to:
- LLM provider initialization issues
- Memory system connectivity problems
- Resource constraints on MAS VM

**Current Status:** Requires further investigation. Voice system works without brain integration but lacks memory-aware responses.

## Current Voice System Health

After fixes:

```json
{
  "status": "healthy",
  "version": "8.1.0",
  "moshi_available": true,
  "moshi_url": "http://localhost:8998",
  "mas_url": "http://192.168.0.188:8001",
  "voice_command_url": "http://192.168.0.188:8001/voice/command",
  "temperature": {"text": 0.4, "audio": 0.6},
  "persona_length": 1046,
  "voice_store_connected": true,
  "map_clients_connected": 0,
  "features": {
    "full_duplex": true,
    "mas_tool_calls": true,
    "memory_cloning": true,
    "session_persistence": true,
    "history_loading": true,
    "crep_voice_control": true
  }
}
```

## Files Modified

1. `config/myca_personaplex_short.txt` - Expanded MYCA persona
2. `services/personaplex-local/personaplex_bridge_nvidia.py`:
   - Added MAS repo to Python path
   - Fixed DATABASE_URL credentials
   - Enhanced error logging in `get_voice_store()`
3. `MINDEX/mindex/migrations/0012_voice_session_store.sql` - Created new migration

## Scripts Created

1. `scripts/_check_memory_tables.py` - Check memory schema tables
2. `scripts/_check_voice_schema.py` - Check voice schema tables
3. `scripts/_apply_voice_migration.py` - Apply voice migration via SSH

## Database Changes (MINDEX VM)

New tables in `memory` schema:
- `memory.voice_sessions`
- `memory.voice_turns`
- `memory.voice_tool_invocations`
- `memory.voice_barge_in_events`

New functions:
- `memory.end_voice_session(session_id, summary)`
- `memory.get_session_with_turns(session_id)`

New view:
- `memory.voice_session_stats`

## Remaining Work

1. **Voice Type:** Implement NATF2 female voice (generate embeddings or switch TTS)
2. **Brain Integration:** Debug MAS brain API timeout for memory-aware responses
3. **Test End-to-End:** Verify voice system works correctly on `/test-voice` page
4. **Deploy:** Commit changes and deploy to production

## Related Documentation

- `docs/VOICE_SYSTEM_FIX_FEB12_2026.md` - Earlier Moshi startup fixes
- `docs/PERSONAPLEX_VOICE_SYSTEM_FEB05_2026.md` - PersonaPlex architecture
- `docs/MAS_VM_ISSUES_AND_FIXES_FEB12_2026.md` - MAS VM cleanup
