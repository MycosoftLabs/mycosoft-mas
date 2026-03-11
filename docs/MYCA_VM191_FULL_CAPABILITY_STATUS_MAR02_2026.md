# MYCA VM 191 Full Capability Status — What's Done, What's Not

**Date**: March 2, 2026  
**Status**: In Progress  
**Related**: [MYCA_PLATFORM_STATUS_AND_GAPS_MAR05_2026](./MYCA_PLATFORM_STATUS_AND_GAPS_MAR05_2026.md), [MYCA_OMNICHANNEL_DIALOGUE_BUS_COMPLETE_MAR06_2026](./MYCA_OMNICHANNEL_DIALOGUE_BUS_COMPLETE_MAR06_2026.md)

---

## Direct Answers to Your Questions

| Question | Answer |
|----------|--------|
| **Text MYCA on Signal / WhatsApp / Discord?** | **Discord yes.** Signal and WhatsApp need setup (signal-cli on 191, Evolution API or WhatsApp integration). |
| **Add her to Signal group chat with team?** | **Not yet.** Requires signal-cli on VM 191 (port 8089), `MYCA_SIGNAL_NUMBER` in env, and group enrollment. |
| **Brain, memory, capabilities?** | **Yes.** MAS orchestrator (188), MINDEX (189), executive agent, personal agency, CommsHub, omnichannel bus are built. |
| **Assign her a task on her PC when asked?** | **Yes, if routed correctly.** Task queue and `POST /tasks` exist. She can execute skills, shell commands (when enabled), and delegate to MAS agents. |
| **Periodic updates in chats or Asana?** | **Partly.** DailyRhythmAgent and n8n workflows exist, but n8n on VM 191 must be running, port references fixed (8100 vs 8000), and workflows imported. Asana needs PAT in env. |

---

## Is This Done?

**No. Not fully.** The architecture and code are in place, but several channels and periodic-report flows need configuration and deployment.

---

## What's Working

| Capability | Status |
|------------|--------|
| MYCA OS on VM 191 (port 8100) | Healthy |
| Discord (bot + webhook) | Working |
| Email (IMAP, schedule@mycosoft.org) | Working |
| Brain (MAS 188, MINDEX 189, executive, memory) | In place |
| Task queue and task submission | Built |
| Personal agency (bounded autonomy) | Complete |
| Omnichannel dialogue bus | Complete |
| CommsHub (channel routing) | Built |

---

## What's Not Working / Needs Setup

| Capability | Blocker |
|------------|---------|
| **Signal** | signal-cli on VM 191 (port 8089), `MYCA_SIGNAL_NUMBER`, `MYCA_SIGNAL_CLI_URL` in `/opt/myca/.env` |
| **WhatsApp** | Evolution API or browser automation + credentials on VM 191 |
| **Slack** | `SLACK_APP_TOKEN` or `MYCA_SLACK_BOT_TOKEN` (xapp-*) in env |
| **Asana** | `ASANA_PAT` or `ASANA_API_KEY` in env (health shows `asana=False`) |
| **Signal group chats** | signal-cli must be registered and added to groups |
| **Periodic reports** | n8n on 191, DailyRhythm workflows imported, port fixes (8100 vs 8000) applied |
| **Task execution on her PC** | Shell execution may be disabled; confirm `MYCA_ENABLE_SHELL` and policies |

---

## What You Need to Do on the LAN

1. **Run status check** from Sandbox (187) or MAS (188):
   ```bash
   python3 scripts/check_myca_vm_status.py
   ```

2. **Add credentials to VM 191** (`/opt/myca/.env`):
   - Slack: `SLACK_APP_TOKEN` or `MYCA_SLACK_BOT_TOKEN`
   - Asana: `ASANA_PAT` or `ASANA_API_KEY`
   - Signal: `MYCA_SIGNAL_NUMBER`, `MYCA_SIGNAL_CLI_URL=http://192.168.0.191:8089`

3. **Install and run signal-cli** on VM 191 (REST API on 8089), register MYCA's number, add to Signal groups.

4. **Import n8n workflows** on VM 191 (port 5678), fix any port references (8100 vs 8000), activate DailyRhythm and health-check workflows.

5. **Pull the branch with port fixes** (if still on a feature branch):
   ```bash
   cd /opt/myca/mycosoft-mas && git pull origin main
   ```

---

## Architecture Summary

- **VM 191**: MYCA OS, Workspace API, n8n, signal-cli (when configured), Evolution API (for WhatsApp when configured)
- **VM 188**: MAS orchestrator, agents, Discord bot (or proxy)
- **VM 189**: MINDEX (Postgres, Redis, Qdrant)
- **CommsHub**: Routes messages across Discord, Signal, WhatsApp, Slack, Asana, email
- **Omnichannel bus**: Inbox polling for all channels
- **Personal agency**: Autonomous tasks with bounds

---

## Related Documents

- [MYCA_PLATFORM_STATUS_AND_GAPS_MAR05_2026](./MYCA_PLATFORM_STATUS_AND_GAPS_MAR05_2026.md)
- [MYCA_OMNICHANNEL_DIALOGUE_BUS_COMPLETE_MAR06_2026](./MYCA_OMNICHANNEL_DIALOGUE_BUS_COMPLETE_MAR06_2026.md)
- [MYCA_BOUNDED_PERSONAL_AGENCY_COMPLETE_MAR06_2026](./MYCA_BOUNDED_PERSONAL_AGENCY_COMPLETE_MAR06_2026.md)
- [VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026](./VM_LAYOUT_AND_DEV_REMOTE_SERVICES_FEB06_2026.md)
