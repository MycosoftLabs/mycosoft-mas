/**
 * Browser Handler -- headless Chromium via Playwright inside sandbox.
 */

interface BrowserResult {
  title?: string;
  url?: string;
  content?: string;
  screenshot?: string;
  error?: string;
}

export class BrowserHandler {
  private browser: any = null;
  private page: any = null;
  private idleTimeout: ReturnType<typeof setTimeout> | null = null;
  private static IDLE_MS = 5 * 60 * 1000;

  async handle(payload: Record<string, unknown>): Promise<BrowserResult> {
    const action = payload.action as string;
    this.resetIdleTimer();

    switch (action) {
      case "navigate":
        return this.navigate(payload.url as string);
      case "click":
        return this.click(payload.selector as string);
      case "type":
        return this.type(payload.selector as string, payload.text as string);
      case "screenshot":
        return this.screenshot();
      case "get_content":
        return this.getContent(payload.selector as string | undefined);
      case "close":
        await this.close();
        return { content: "closed" };
      default:
        return { error: `Unknown browser action: ${action}` };
    }
  }

  private async ensureBrowser(): Promise<void> {
    if (!this.browser) {
      const pw = await import("playwright-core");
      this.browser = await pw.chromium.launch({
        headless: true,
        args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
      });
      this.page = await this.browser.newPage();
    }
  }

  private async navigate(url: string): Promise<BrowserResult> {
    await this.ensureBrowser();
    await this.page.goto(url, { waitUntil: "domcontentloaded", timeout: 30_000 });
    return {
      title: await this.page.title(),
      url: this.page.url(),
      content: (await this.page.textContent("body"))?.slice(0, 2000),
    };
  }

  private async click(selector: string): Promise<BrowserResult> {
    await this.ensureBrowser();
    await this.page.click(selector, { timeout: 5000 });
    return {
      title: await this.page.title(),
      url: this.page.url(),
    };
  }

  private async type(selector: string, text: string): Promise<BrowserResult> {
    await this.ensureBrowser();
    await this.page.fill(selector, text, { timeout: 5000 });
    return {
      title: await this.page.title(),
      url: this.page.url(),
    };
  }

  private async screenshot(): Promise<BrowserResult> {
    await this.ensureBrowser();
    const buf: Buffer = await this.page.screenshot({ fullPage: true });
    return {
      screenshot: buf.toString("base64"),
      title: await this.page.title(),
      url: this.page.url(),
    };
  }

  private async getContent(selector?: string): Promise<BrowserResult> {
    await this.ensureBrowser();
    const content = selector
      ? await this.page.textContent(selector)
      : await this.page.content();
    return {
      content: typeof content === "string" ? content.slice(0, 5000) : "",
      title: await this.page.title(),
      url: this.page.url(),
    };
  }

  async close(): Promise<void> {
    if (this.idleTimeout) clearTimeout(this.idleTimeout);
    if (this.browser) {
      await this.browser.close().catch(() => {});
      this.browser = null;
      this.page = null;
    }
  }

  private resetIdleTimer(): void {
    if (this.idleTimeout) clearTimeout(this.idleTimeout);
    this.idleTimeout = setTimeout(() => this.close(), BrowserHandler.IDLE_MS);
  }
}
