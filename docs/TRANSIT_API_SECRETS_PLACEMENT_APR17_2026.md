# Transit API keys — where to set them (no key values) — Apr 17, 2026

**Status:** Operational checklist  
**Related:** `WEBSITE/website` Next.js API routes under `app/api/transit/`

## Security

- **Never** commit key values, password manager exports, or “master key files” to git.
- If keys were pasted into chat, email, or a ticket, **treat them as potentially exposed** and **rotate** them in each agency’s developer portal when policy requires.
- Store values only in: **GitHub `production` environment secrets**, **Sandbox VM** `/opt/mycosoft/website/.env` (or compose env), and **local** `WEBSITE/website/.env.local` (gitignored).

## Environment variable names (website)

These match `process.env.*` in `app/api/transit/*/route.ts`:

| Variable | Used by | Notes |
|----------|---------|--------|
| `BART_API_KEY` | BART | Query `key=`; a long-standing public sandbox key exists in code as dev fallback — still set a dedicated key in production. |
| `CTA_TRAIN_TRACKER_API_KEY` | CTA Train | CTA Bus uses a different portal when restored. |
| `TRANSIT_511_API_KEY` | 511 SF Bay | 511 operator feeds. |
| `WMATA_API_KEY` | WMATA | Header `api_key` on WMATA GTFS-RT URLs. |
| `MARTA_API_KEY` | MARTA | Query `apiKey=` on MARTA GTFS-RT. |
| `TRIMET_API_KEY` | TriMet | Per TriMet API registration. |
| `MBTA_API_KEY` | MBTA | Optional; open `.pb` works — key can improve REST rate limits. |

Agencies with **no key in code** (MTA, Amtrak, SEPTA, Metrolink, DART, etc.) do not need env vars for those read-only public feeds until a route is added that requires a key.

## Optional / future

- `WMATA_API_KEY_SECONDARY` — **wired:** `app/api/transit/wmata/route.ts` retries all feeds with the secondary key if the primary `fetchMultipleFeeds` result is not ok.
- `SWIFTLY_API_KEY` — LA Metro (and other Swiftly agencies) when issued.
- `INAT_API_TOKEN` / `MINDEX_INAT_API_KEY` — iNaturalist (MINDEX `inat_api_token` in `mindex` API settings) for higher rate limits on cache ingest.

## Rollout

1. Add each secret in **GitHub** → **Settings** → **Environments** → **production** (same names as above).
2. Add the same keys to **Sandbox** website `.env` used by Docker Compose, then `docker compose ... up -d --force-recreate` for the website service.
3. **Purge Cloudflare** cache after production deploys that change server-side env (Next.js bakes public env at build time; server secrets come from the runtime environment on the VM).

**Do not** paste live keys into this repository’s markdown, issues, or PR descriptions.
