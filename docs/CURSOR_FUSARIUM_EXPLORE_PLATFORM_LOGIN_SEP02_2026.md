# Cursor Fusarium Explore Platform Login — Sep 02, 2026

**Date:** September 2, 2026  
**Status:** Public path is live on the website origin. Loopback twins-host remains the local rollback.  
**Classification:** Commercial UNCLASSIFIED  
**Authority:** Morgan Rockcoons (CEO / CTO / COO / SAO). RJ Ricasata is CFO, not COO.  
**CUI:** None.

## Exact public CTA href

| Host | Exact href |
|---|---|
| **Apex (Explore default)** | `https://mycosoft.com/fusarium/login` |
| **Sandbox equivalent** | `https://sandbox.mycosoft.com/fusarium/login` |

No new DNS name. Civilian `/login` is unchanged. Launchpad stays at `/fusarium/launchpad`.

Website source: `WEBSITE/website/app/defense/fusarium/explore-platform-cta.tsx` via `getFusariumLoginHref()` (`lib/fusarium-operator-login.ts`).

## Public operator routes (website origin)

| Role | URL | Result |
|---|---|---|
| Operator login | `https://mycosoft.com/fusarium/login` | **200** Fusarium owner sign-in (existing Supabase project). Anonymous stay here. |
| Operator dashboard | `https://mycosoft.com/fusarium/app` | Anonymous **307** → `/fusarium/login?redirectTo=%2Ffusarium%2Fapp`. Owner session proceeds. Signed-in non-owners get honest **403**. |
| Launchpad (untouched) | `https://mycosoft.com/fusarium/launchpad` | **200** marketing/product. |
| Civilian account login | `https://mycosoft.com/login` | **200** unchanged. |

Dashboard after owner login is the website-mounted console at `/fusarium/app` (BFF + existing alpha surfaces). Twins-host on loopback is **not** the public origin.

## Claude P0s on this origin

Anonymous `GET /api/natureos/devices/telemetry` and `GET /api/devices/network` → **401** JSON `{ error, data_state: "withheld", access: { required_role: "owner" } }`. No device rows, coordinates, serial ports, or `agent_url`. `requireFusariumOwner()` runs before any MAS/LAN/serial fetch. Local-dev admin cookies are not owner proof. Service-role is not in `NEXT_PUBLIC_*` or login HTML.

## Loopback rollback (kept)

| Role | URL | Health |
|---|---|---|
| Login green UI | `http://127.0.0.1:8212` | leave running |
| Login green API | `http://127.0.0.1:8211` | leave running |
| Owner login rollback | `http://127.0.0.1:8212/login?redirectTo=%2Ffusarium` | do not tear down 8212/8112/8012 |

Do not stop 8212/8211, 8112/8111, or 8012/8011 unless Morgan says so.

## Auth

No new Supabase project. Env **names** only: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`. Dashboard entry: **Morgan owner email only** (`morgan@mycosoft.org` / `OWNER_ALLOWED_EMAILS`). Owner password was **not** used or logged in this lane.

## Not done

- Phylogeny / Earth Simulator / CREP / AWS bake / hardware  
- Developer Fusarium tree reset  
- New hostname `fusarium.mycosoft.com`
