# bridges/

Cross-language memory bridge implementations for connecting the MAS Python memory system to other platform components.

## Purpose

These bridge files provide memory system interoperability between the MAS (Python) and other Mycosoft platform components written in different languages:

| File | Language | Connects To |
|------|----------|-------------|
| `memory_bridge.cs` | C# | NatureOS (.NET 8.0) |
| `memory_bridge.hpp` | C++ | MycoBrain ESP32 firmware |
| `memory_bridge.ts` | TypeScript | Website (Next.js) |

## How It Works

Each bridge implements a common interface for reading/writing to the MAS 6-layer memory system via the MAS API (`http://192.168.0.188:8001/api/memory/`). This allows NatureOS, MycoBrain, and the Website to share memory context with the MAS agents.

## Related Code

- MAS memory system: `mycosoft_mas/memory/`
- Memory API router: `mycosoft_mas/core/routers/memory_api.py`
- Memory integration API: `mycosoft_mas/core/routers/memory_integration_api.py`
