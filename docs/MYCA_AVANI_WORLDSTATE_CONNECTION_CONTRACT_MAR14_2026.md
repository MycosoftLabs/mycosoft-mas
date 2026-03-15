# MYCA/AVANI Live Worldstate Connection Contract (Mar 14, 2026)

**Status:** Canonical  
**Product:** Paid live worldstate access for external agents  
**Pricing:** $1/minute (prepaid minutes via Stripe)

---

## Product Scope

- **What is sold:** Live worldstate connection time to **MYCA** and **AVANI** only. External agents pay per active minute of connection.
- **What is not included at launch:** Broad MAS capability access; other paid invoke routes remain unexposed until verified.

---

## Session Lifecycle

All session endpoints live under MAS `BASE_URL/api/raas/worldstate/` and require header `X-API-Key: <agent_api_key>`.

| Action | Endpoint | Method | Description |
|--------|----------|--------|-------------|
| Start session | `/api/raas/worldstate/start` | POST | Creates a paid session; first heartbeat deducts 1 minute. |
| Heartbeat | `/api/raas/worldstate/heartbeat` | POST | Keeps session active; 1 minute deducted per elapsed minute. |
| Stop session | `/api/raas/worldstate/stop` | POST | Stops session and finalizes minutes used. |
| Balance | `/api/raas/worldstate/balance` | GET | Returns current minute balance (balance_minutes, total_purchased_minutes, total_used_minutes). |
| Usage | `/api/raas/worldstate/usage` | GET | Returns balance + active_session_id + recent_sessions (query: `limit`). |

---

## 402 Payment Required

When an agent has **insufficient balance** (e.g. no remaining minutes or session time would exceed balance):

- **Start** and **heartbeat** return HTTP **402 Payment Required** with a JSON body describing the required payment/balance.
- The client must purchase more minutes (via website Stripe checkout) and retry.

---

## Authentication

- Every request to the worldstate session endpoints must include: `X-API-Key: <agent_api_key>`.
- The API key is issued after agent registration and Stripe purchase; it is tied to the agent’s prepaid minute ledger.

---

## References

- **MAS router:** `mycosoft_mas/raas/session_lifecycle.py`
- **Service catalog:** `live_worldstate_connection` in `mycosoft_mas/raas/service_catalog.py`
- **API catalog:** `docs/API_CATALOG_FEB04_2026.md` (RaaS Worldstate Sessions section)
- **Website:** `/agent` (offer + checkout), `/agent/dashboard` (balance & usage)
