# Security Review Notes

## Scope
- Performed a targeted scan for common secret patterns in the working tree.
- Checked Git history for specific exposed values that appeared in docs.

## Commands Run
- `rg -n "AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|AIza[0-9A-Za-z\-_]{35}|sk_live_[0-9a-zA-Z]{24}|BEGIN RSA PRIVATE KEY|BEGIN OPENSSH PRIVATE KEY|PRIVATE KEY-----|xox[baprs]-[0-9A-Za-z-]{10,48}|ghp_[0-9A-Za-z]{36}|gho_[0-9A-Za-z]{36}|ghs_[0-9A-Za-z]{36}|ghr_[0-9A-Za-z]{36}" .`
- `rg -n "(api[_-]?key|secret|token|password|private key|BEGIN [A-Z ]*PRIVATE KEY|xox[baprs]-|sk-[a-zA-Z0-9]{20,}|sk_live_|sk_test_)" docs README.md *.md`
- `rg -n "Mushroom1!Mushroom1!|AIzaSyA9wzTz5MiDhYBdY1vHJQtOnw9uikwauBk" docs`
- `git log -G "AIzaSyA9wzTz5MiDhYBdY1vHJQtOnw9uikwauBk" --patch -- docs/API_KEYS_STATUS.md docs/EARTH_SIMULATOR_VISION_TASKS.md`
- `git log -G "Mushroom1!Mushroom1!" --patch -- docs`

## Findings
- A Google Maps API key was present in documentation.
- A hardcoded SSH password for VM access was present in multiple deployment/security docs.
- These items also appeared in Git history, so history rewriting is required if this repo is public.

## Recommendations
1. Rotate the affected credentials in their respective provider dashboards.
2. Rewrite Git history to fully purge the exposed values (e.g., `git filter-repo`), then force-push.
3. Add automated secret scanning (e.g., gitleaks/trufflehog) to CI to prevent reintroduction.
