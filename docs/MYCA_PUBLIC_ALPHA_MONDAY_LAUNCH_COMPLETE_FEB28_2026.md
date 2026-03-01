# MYCA Public Alpha Monday Launch – Complete

**Date**: February 28, 2026  
**Author**: MYCA  
**Status**: Complete

## Overview

Completion report for the MYCA Public Alpha Monday Launch plan. This documents the final changes, verification steps, and follow-ups for the demo telemetry loop and end-to-end voice test readiness.

## Scope Delivered

- Added a telemetry tool to the MAS tool pipeline so MYCA can query live device telemetry from MINDEX.
- Completed the demo loop for device telemetry Q&A by wiring the new tool into ToolExecutor.
- Brought the test-voice stack online locally and verified diagnostics + voice session connectivity.

## Changes Delivered

### MAS tool pipeline

- Added `query_device_telemetry` tool definition and handler in `mycosoft_mas/llm/tool_pipeline.py`.
- Tool calls `MINDEX_API_URL` (defaulting to VM 189) and uses `MINDEX_API_KEY` when available.

### Voice system (local test)

- Reconfigured website voice bridge env vars to local (`localhost:8999`) for the local voice test session.
- Started local Moshi + PersonaPlex Bridge and verified test-voice diagnostics and session connection.

## Verification

### Demo loop (telemetry tool)

- New tool registered: `query_device_telemetry`
- Handler: `ToolExecutor._execute_device_telemetry` calls MINDEX latest telemetry endpoint
- Expected behavior: tool returns latest device sample JSON or error if device not found

### Voice test (test-voice page)

- `http://localhost:3010/api/test-voice/diagnostics` shows all services OK
- `http://localhost:3010/test-voice` shows "All systems ready" and connects to session

## Follow-ups / Notes

- If you prefer GPU node (190) for bridge hosting, revert local bridge URLs in `WEBSITE/website/.env.local` to the GPU node URLs and restart the dev server.
- Local Moshi + Bridge are GPU-heavy; shut them down when done using `scripts/dev-machine-cleanup.ps1 -KillStaleGPU`.

## Related Documents

- `docs/VOICE_TEST_QUICK_START_FEB18_2026.md`
- `docs/MYCA_VOICE_TEST_SYSTEMS_ONLINE_FEB18_2026.md`
- `.cursor/plans/myca_public_alpha_monday_launch_8aee395b.plan.md`
