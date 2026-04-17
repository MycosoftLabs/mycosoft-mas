# Integration Patch Plan – MYCA Harness 2026

This document outlines the concrete steps required to integrate the STATIC video tool (MYCA’s YouTube connector), the static system, turbo‑quant compression, intention‑brain consciousness, PersonaPlex full‑duplex voice, Nemotron as the in‑house LLM, MINDEX/Supabase and the Nature Learning Model (NLM) into the existing MYCA harness.

## 1 Repository Alignment

1. **Create a new harness package** within the myca\_harness\_blueprint codebase. This package will be installed as part of the MAS monorepo. It should expose the public API via mycosoft\_mas.harness.

2. **Mirror directory structure** according to MAS conventions. At a minimum, include models.py, engine.py, router.py, planner.py, evaluator.py, optimization.py, api.py and new integration modules described below.

3. **Add \_\_init\_\_.py files** to ensure each folder is a valid Python package.

## 2 Nemotron Integration

1. Implement harness/nemotron\_client.py with a NemotronClient class. The class should:

2. Manage authentication and endpoint configuration for the Nemotron 3 VoiceChat model.

3. Expose an async generate() method that accepts a prompt string, optional system instructions, and streaming flags; returns a generator of tokens.

4. Handle pre‑ and post‑processing, including optional turbo‑quant compression (see section 5).

5. Update router.py to include a RouteType.NEMOTRON and send all non‑static, language‑heavy packets to this route.

6. Modify engine.py to instantiate NemotronClient during startup based on configuration (e.g., environment variables for API keys or local inference endpoints).

7. Ensure that Nemotron outputs can be passed to persona\_plex.py for speech synthesis when appropriate.

## 3 PersonaPlex Integration

1. Implement harness/persona\_plex.py with a PersonaPlexInterface class. Key responsibilities:

2. Manage voice embedding selection (NATF0 … VARM4) and persona prompts as described in the PersonaPlex documentation[\[1\]](https://github.com/NVIDIA/personaplex#:~:text=Voices).

3. Provide transcribe() and speak() methods to convert between audio streams and text. transcribe() should expose a streaming API for real‑time ASR; speak() should accept text and return audio buffers.

4. Support full‑duplex operation: allow speak() to run even while transcribe() is listening.

5. Add a voice route to router.py that forwards packets containing audio data to PersonaPlex for transcription. After LLM reasoning or static lookup, send the response back through PersonaPlex.

6. Integrate a heartbeat mechanism so that the manager can interrupt the Nemotron call when the user interrupts the agent mid‑sentence.

## 4 STATIC Video Tool

1. Implement harness/static\_video\_tool.py with a StaticVideoTool class. It should:

2. Use Google’s YouTube Data API to search videos and fetch metadata based on a query string.

3. Download captions or auto‑generated transcripts using the YouTube API or a third‑party library.

4. Expose a search() method that returns video metadata and a transcribe() method to download transcripts.

5. Include caching logic to avoid re‑downloading the same transcript.

6. Register a RouteType.STATIC\_VIDEO in router.py. When a packet’s intent corresponds to watching or summarising a video, route to this worker.

7. Provide fallback to Nemotron summarisation on the returned transcript.

## 5 Static System

1. Implement harness/static\_system.py exposing a StaticSystem class. It should:

2. Load a YAML or JSON file containing canonical responses for common queries (definitions, safety policies, device protocols).

3. Expose a lookup(query: str) \-\> Optional\[str\] method returning a static answer or None.

4. Update router.py to check the static system first. If a result exists, return it immediately via PersonaPlex (for voice) or as plain text (for API).

5. Provide an update mechanism where new static answers can be added via configuration rather than code changes.

## 6 Turbo‑Quant Compression

1. Implement harness/turbo\_quant.py with a TurboQuantCompressor class. The class should define compress(prompt: str) \-\> bytes and decompress(data: bytes) \-\> str. Actual compression algorithm may be a placeholder; document that details are under NDA.

2. Expose a configuration flag enable\_turbo\_quant (e.g., via environment variable or execution contract). When set, wrap all Nemotron prompts and responses with turbo‑quant compression.

3. Integrate logging to record compression ratio and time taken for each operation for later performance analysis.

## 7 Intention Brain Consciousness

1. Implement harness/intention\_brain.py with an IntentionBrain class. Key components:

2. A persistent data structure (e.g., SQLite DB or file‑backed store) for storing goals, tasks, hypotheses and their statuses.

3. Methods update\_goal(goal\_id, status) and get\_next\_task() to manage the current intention stack.

4. Hooks for receiving signals from NLM (anomalies, anomalies) and Nemotron outputs. For example, if NLM predicts a high anomaly score[\[2\]](https://github.com/MycosoftLabs/NLM#:~:text=Running%20the%20Model), the intention brain should prioritise safety actions.

5. Modify planner.py to consult the intention brain when compiling execution plans. Contracts should align with current goals.

## 8 MINDEX and Supabase Integration

1. Implement harness/mindex\_client.py with a MindexClient class. It should:

2. Use Supabase’s Python SDK to connect to the MINDEX PostgreSQL instance. Provide functions to fetch records (e.g., by species ID, timestamp, geohash) and insert new records with provenance information.

3. Verify cryptographic proofs returned by MINDEX by recomputing Merkle roots where possible.

4. Expose a record\_execution(run\_id, events) method to write harness execution metadata into MINDEX for later meta‑harness optimisation.

5. Update evaluator.py so that when a worker produces a factual answer derived from MINDEX, the evaluator cross‑checks against MINDEX entries. If there is a mismatch, flag the result for manual review.

6. Add environment variables for Supabase URL and service key in deployment scripts.

## 9 NLM Interface

1. Implement harness/nlm\_interface.py with an NlmInterface class. It should:

2. Wrap the RootedFrameBuilder and NLMWorldModel from the NLM package[\[3\]](https://github.com/MycosoftLabs/NLM#:~:text=NLM%20%E2%80%94%20Nature%20Learning%20Model)[\[2\]](https://github.com/MycosoftLabs/NLM#:~:text=Running%20the%20Model).

3. Provide build\_frame(raw\_data: dict, lat: float, lon: float, alt: float) \-\> RootedNatureFrame that returns a merkle‑rooted frame. This uses deterministic physics/chemistry/biology transforms and fingerprint extraction.

4. Provide predict(frame: RootedNatureFrame) \-\> dict that returns next‑state predictions, anomaly scores and grounding confidences.

5. Register a RouteType.NLM in router.py. Packets containing raw sensor data should be routed here.

6. Ensure the AVANI guardian (if present) can intercept NLM outputs and veto any unsafe actions[\[3\]](https://github.com/MycosoftLabs/NLM#:~:text=NLM%20%E2%80%94%20Nature%20Learning%20Model).

## 10 Testing and Validation

1. Write unit tests for each new module under tests/ using pytest. Mock external services (Nemotron, PersonaPlex, STATIC video tool, Supabase) using fixtures.

2. Add integration tests for complete flows, such as "voice query → PersonaPlex → Nemotron → static system/NLM → MINDEX write".

3. Use scripts/ or CI pipelines to run tests on each pull request. Include performance benchmarks to compare token usage and latency with and without turbo‑quant compression.

## 11 Documentation

1. Update the README.md and API documentation to reflect the new modules and configuration options.

2. Provide examples demonstrating how to use the STATIC video tool, how to enable turbo‑quant compression and how to register new static system entries.

3. Document the safety considerations for MINDEX writes and NLM predictions. Include references to the NLM architecture and AVANI guardian requirements[\[3\]](https://github.com/MycosoftLabs/NLM#:~:text=NLM%20%E2%80%94%20Nature%20Learning%20Model).

By following this patch plan, engineers can methodically integrate the requested subsystems into the existing harness while preserving modularity, testability and safety.

---

[\[1\]](https://github.com/NVIDIA/personaplex#:~:text=Voices) GitHub \- NVIDIA/personaplex: PersonaPlex code. · GitHub

[https://github.com/NVIDIA/personaplex](https://github.com/NVIDIA/personaplex)

[\[2\]](https://github.com/MycosoftLabs/NLM#:~:text=Running%20the%20Model) [\[3\]](https://github.com/MycosoftLabs/NLM#:~:text=NLM%20%E2%80%94%20Nature%20Learning%20Model) GitHub \- MycosoftLabs/NLM: A grounded sensory world model that learns from raw physical reality — wavelengths, waveforms, voltages, gas concentrations, temperature gradients, pressure fields — and predicts what happens next. · GitHub

[https://github.com/MycosoftLabs/NLM](https://github.com/MycosoftLabs/NLM)