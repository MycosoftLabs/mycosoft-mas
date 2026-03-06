# BoostVC Management Rights Compliance Checklist (Mar 2026)

**Date:** 2026-03-05  
**Purpose:** Ensure Mycosoft meets BoostVC management-rights letter requirements.

---

## Required Obligations

| # | Obligation | Status | Notes |
|---|------------|--------|-------|
| 1 | **Annual operating plan shared** | Track | Due annually; share with BoostVC per schedule |
| 2 | **Board notices/minutes shared** | Track | Share after each board meeting |
| 3 | **Material business changes communicated** | Track | Notify promptly on material events |
| 4 | **Books and records accessible** | Track | Maintain audit trail; provide on request |

---

## Annual Operating Plan

- **Due:** Per BoostVC agreement (typically January)
- **Config:** `config/board_meetings.yaml` → `compliance.annual_operating_plan_due`
- **Action:** MYCA drafts from MINDEX; Morgan reviews; send to BoostVC contact

---

## Board Materials

- **Package output:** `docs/board/`
- **Contents:** Agenda, financials, plan updates, compliance checklist
- **Naming:** `board_package_YYYY-MM-DD.md` (dated)
- **Config:** `config/board_meetings.yaml` → `meetings`

---

## Material Business Changes

Notify BoostVC promptly when:

- Significant fundraising
- Key personnel changes
- Pivot or major strategy shift
- Legal/compliance events
- Financial distress signals

---

## Books and Records

- Financials in MINDEX / accounting system
- Board minutes in `docs/board/`
- Investor communications in email / Notion
- Ensure MYCA can generate reports on request

---

## Related

- `templates/investor_update.md` — quarterly investor update template
- `config/board_meetings.yaml` — board meeting schedule
- `docs/board/` — board package output folder
