# MYCA Voice Test – Quick Start (Feb 18, 2026)

## Run servers in external terminals (not Cursor)

**Dev server, Moshi, and Bridge** should be run in **external** terminals (e.g. separate PowerShell or Windows Terminal windows), not inside Cursor's integrated terminal. That keeps Cursor responsive and lets the services run independently. See `.cursor/rules/run-servers-externally.mdc`.

---

## 1. Start dev server (in an external window)

Open a **new** PowerShell or Windows Terminal window (outside Cursor), then from the **website** repo:

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website
.\scripts\start-dev.ps1
```

Or:

```powershell
npm run dev:next-only
```

To launch from Cursor in one shot (opens external window):  
`Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website'; npm run dev:next-only"`

Open **http://localhost:3010/test-voice**.

---

## 2. Start the entire voice system (single script)

From the **MAS repo** in an **external** terminal (PowerShell or Windows Terminal), run:

```powershell
cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
python scripts/start_voice_system.py
```

This single script starts **Moshi** (port 8998) and **PersonaPlex Bridge** (port 8999) if they are not already running. Each runs in its own console window. The script checks MAS (188:8001) and prints when the voice system is ready.

### GPU node (192.168.0.190) or remote Moshi

If Moshi runs on another host (e.g. GPU node), start only the Bridge on this PC with Moshi pointed at that host:

```powershell
$env:MOSHI_HOST="192.168.0.190"; $env:MOSHI_PORT="8998"
python scripts/start_voice_system.py
```

Or on the GPU node, run the bridge there and set in website `.env.local`:

- `PERSONAPLEX_BRIDGE_URL=http://192.168.0.190:8999`
- `NEXT_PUBLIC_PERSONAPLEX_BRIDGE_WS_URL=ws://192.168.0.190:8999`

---

## 3. Verify MAS (188:8001)

MAS must be reachable from the Next.js server:

```powershell
Invoke-RestMethod -Uri "http://192.168.0.188:8001/health"
```

---

## 4. Run diagnostics on test-voice

1. Open http://localhost:3010/test-voice.
2. Click **Refresh** in the Services panel.
3. All four services should show **ONLINE**: Moshi (via Bridge), Bridge, MAS Consciousness, Memory Bridge.
4. Click **Start MYCA Voice**.
5. Speak; you should hear MYCA’s response.

---

## If it still doesn’t work

| Symptom | Fix |
|---------|-----|
| Bridge offline | Ensure bridge process is running at the configured host/port. Check `.env.local` `PERSONAPLEX_BRIDGE_URL` and `NEXT_PUBLIC_PERSONAPLEX_BRIDGE_WS_URL`. |
| Moshi offline | Moshi must be running and reachable by the bridge. Set `MOSHI_HOST` / `MOSHI_PORT` on the bridge host. |
| WebSocket error | Browser must reach the bridge WebSocket URL. If bridge is on 192.168.0.190, the dev machine must be on the same LAN. |
| No audio playback | Check browser console for decoder/worker errors. Ensure `/assets/decoderWorker.min.js` and `/assets/encoderWorker.min.js` exist. Allow mic permission. |
| MAS timeout | Ensure MAS VM (188) is up and reachable. Diagnostics use 18s timeout for MAS. |
