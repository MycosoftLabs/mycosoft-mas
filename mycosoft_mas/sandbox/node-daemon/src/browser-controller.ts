/**
 * Browser Controller -- Playwright-based browser automation.
 * Higher-level abstraction over browser-handler for structured control.
 */

export class BrowserController {
  private browser: any = null;
  private page: any = null;

  async launch(): Promise<void> {
    if (this.browser) return;
    const pw = await import("playwright-core");
    this.browser = await pw.chromium.launch({
      headless: true,
      args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
    });
  }

  async newPage(url: string): Promise<{ title: string; url: string }> {
    await this.launch();
    this.page = await this.browser.newPage();
    await this.page.goto(url, { waitUntil: "domcontentloaded", timeout: 30_000 });
    return { title: await this.page.title(), url: this.page.url() };
  }

  async click(selector: string): Promise<void> {
    if (!this.page) throw new Error("No page open");
    await this.page.click(selector, { timeout: 5000 });
  }

  async type(selector: string, text: string): Promise<void> {
    if (!this.page) throw new Error("No page open");
    await this.page.fill(selector, text);
  }

  async screenshot(): Promise<string> {
    if (!this.page) throw new Error("No page open");
    const buf: Buffer = await this.page.screenshot({ fullPage: true });
    return buf.toString("base64");
  }

  async getContent(selector?: string): Promise<string> {
    if (!this.page) throw new Error("No page open");
    if (selector) {
      return (await this.page.textContent(selector)) ?? "";
    }
    return await this.page.content();
  }

  async close(): Promise<void> {
    if (this.page) {
      await this.page.close().catch(() => {});
      this.page = null;
    }
    if (this.browser) {
      await this.browser.close().catch(() => {});
      this.browser = null;
    }
  }
}
