import { test, expect } from "@playwright/test";

test("dashboard loads", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/MYCA Dashboard/i);
  await expect(page.getByRole("button", { name: "Talk to MYCA" })).toBeVisible();
});

test("theme toggle works", async ({ page }) => {
  await page.goto("/");
  // The toggle has aria-label like "Switch to light mode" / "Switch to dark mode"
  const themeToggle = page.getByRole("button", { name: /Switch to (light|dark) mode/i });
  await expect(themeToggle).toBeVisible();
  await themeToggle.click();
  // After toggle, label should flip
  await expect(page.getByRole("button", { name: /Switch to (light|dark) mode/i })).toBeVisible();
});

test("Talk to MYCA responds with identity + pronunciation", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Talk to MYCA" }).click();

  await expect(page.getByRole("heading", { name: "MYCA" })).toBeVisible();
  const input = page.getByRole("textbox", { name: "Type a message..." });
  await input.fill("What is your name and how do you pronounce it?");
  await page.getByRole("button", { name: "Send message" }).click();

  // Look for response containing MYCA and my-kah
  await expect(page.getByText(/I'm MYCA/i)).toBeVisible();
  await expect(page.getByText(/my-kah/i)).toBeVisible();
});

