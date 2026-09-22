import { expect, test } from "@playwright/test";

test("register lands on dashboard empty state", async ({ page, request }) => {
  const health = await request.get("http://127.0.0.1:8000/health").catch(() => null);
  test.skip(!health || !health.ok(), "API not running");
  const email = `e2e-${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByPlaceholder("Name").fill("Ayomide");
  await page.getByPlaceholder("Organization").fill("Northwind");
  await page.getByPlaceholder("Email").fill(email);
  await page.getByPlaceholder("Password (8+ characters)").fill("correcthorse");
  await page.getByText("I agree to the").click();
  await page.getByText("I acknowledge the").click();
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("No devices yet")).toBeVisible({ timeout: 15000 });
});
