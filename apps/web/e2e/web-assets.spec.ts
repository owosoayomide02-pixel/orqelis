import { test, expect } from "@playwright/test";

test("web assets: add domain → verify → hunter → findings", async ({ page }) => {
  const email = `wa-${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/^password/i).fill("correcthorse");
  await page.getByLabel(/organization/i).fill("WebAsset Co");
  const terms = page.getByLabel(/terms/i);
  if (await terms.count()) await terms.check();
  const privacy = page.getByLabel(/privacy/i);
  if (await privacy.count()) await privacy.check();
  await page.getByRole("button", { name: /create|register|sign up/i }).click();
  await page.waitForURL(/dashboard/, { timeout: 30000 });

  await page.goto("/dashboard/web-assets/new");
  await page.getByLabel(/domain/i).fill("playwright-scan.example");
  await page.getByRole("button", { name: /add domain/i }).click();
  await expect(page.getByText(/prove ownership|txt/i)).toBeVisible({ timeout: 15000 });

  const testVerify = page.getByRole("button", { name: /test-mode verify/i });
  if (await testVerify.count()) {
    await testVerify.click();
    await expect(page.getByText(/verified/i)).toBeVisible({ timeout: 15000 });
  }

  await page.getByRole("button", { name: /^hunter$/i }).click();
  await expect(page.getByText(/hunter scan|status/i)).toBeVisible({ timeout: 10000 });
  await expect(page.getByText(/findings/i).first()).toBeVisible({ timeout: 30000 });
});
