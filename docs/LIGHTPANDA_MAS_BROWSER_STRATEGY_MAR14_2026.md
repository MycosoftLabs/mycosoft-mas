# Lightpanda MAS Browser Strategy

**Date:** March 14, 2026  
**Status:** Reference — integration policy and operational notes  
**Source:** [Lightpanda browser (GitHub)](https://github.com/lightpanda-io/browser)

---

Yes — it's worth incorporating into MAS, but not as your only browser runtime.

Lightpanda is an open-source headless browser aimed at AI and automation, exposes a CDP server, and claims compatibility with Playwright, Puppeteer, and chromedp. Its README also claims much lower memory use and faster execution than Chrome for its benchmarked workload. ([GitHub][1])

The catch is the important part: Lightpanda explicitly says it is **Beta**, still a work in progress, with partial Web API support and possible crashes. The repo lists implemented pieces like JS via V8, DOM APIs, XHR/fetch, cookies, custom headers, proxy support, network interception, and optional `robots.txt` obedience, but it does **not** present itself as a fully mature Chromium substitute yet. ([GitHub][1])

For MAS, the smart move is:

1. **Use Lightpanda as a specialized browser worker**
   * fast scraping
   * low-RAM parallel agent browsing
   * structured extraction jobs
   * bulk web research
   * link traversal for autonomous agents

2. **Keep Chromium/Playwright as the fallback lane**
   * auth-heavy sites
   * weird JS apps
   * sites that depend on broader Web API coverage
   * anything brittle or revenue-critical

3. **Wrap it behind a browser abstraction in MAS**
   * `BrowserProvider = lightpanda | chromium`
   * task router chooses engine by job type
   * automatic retry on Chromium if Lightpanda fails

That gives you the upside without betting the farm on a beta browser.

## Operational issues to account for

* **License**: The repo is AGPL-3.0, which matters if MAS is distributed or exposed in ways that trigger copyleft obligations. Don't casually weld this into proprietary components without a licensing review. ([GitHub][1])
* **Telemetry**: Lightpanda says telemetry is on by default and can be disabled with `LIGHTPANDA_DISABLE_TELEMETRY=true`. For MAS, disable that by default in every environment. ([GitHub][1])
* **Platform/build maturity**: The README highlights binaries for Linux x86_64 and macOS aarch64, Docker images for amd64/arm64, and Windows via WSL2 rather than native Windows. It is written in Zig and depends on a more custom build chain than a standard Node-only browser stack. ([GitHub][1])

## Recommendation for the stack

**Add it to MAS as `browser-lightpanda`**, a containerized service with:

* CDP on an internal port
* telemetry disabled
* outbound proxy support
* per-job ephemeral browser contexts
* timeout / crash detection
* automatic failover to Chromium
* job tags like `fast_scrape`, `interactive_scrape`, `login_flow`, `visual_render`

### Suggested MAS role layout

* **Web Research Agent** → Lightpanda first
* **Scraper / Intelligence Agent** → Lightpanda first
* **QA / UI Validation Agent** → Chromium first
* **Authenticated Workflow Agent** → Chromium first
* **Fallback Orchestrator Rule** → retry on alternate engine

In plain English: Lightpanda is a good knife. It is not yet the whole toolbox.

### First integration policy

* Default to Lightpanda for public-page fetch, crawling, extraction, and agentic browsing.
* Default to Chromium for login, payments, dashboards, drag-and-drop apps, canvas-heavy sites, and anything visually sensitive.
* Record success/failure per domain so MAS learns which engine to use over time.

### Follow-on

Draft the exact MAS integration package: Docker Compose service, Node browser adapter, agent routing rules, and a Cursor-ready implementation plan.

---

[1]: https://github.com/lightpanda-io/browser "GitHub - lightpanda-io/browser: Lightpanda: the headless browser designed for AI and automation"
