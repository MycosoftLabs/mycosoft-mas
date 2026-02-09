# templates/

Jinja2 HTML templates for the MAS web dashboard.

## Contents

| File | Purpose |
|------|---------|
| `dashboard.html` | Main MAS monitoring dashboard (served by `mycosoft_mas/web/dashboard.py`) |

## Notes

- These are server-rendered HTML templates, not React/Next.js components.
- The primary user-facing UI is the Next.js website (`WEBSITE/website/`). These templates are for internal MAS monitoring only.
- Additional dashboard templates exist in `mycosoft_mas/monitoring/templates/` and `mycosoft_mas/web/templates/`.
