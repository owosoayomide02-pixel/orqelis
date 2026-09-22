import { expect, test } from "@playwright/test";

test("public homepage hero", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("SECURITY FOR THE")).toBeVisible();
  await expect(page.getByText("INTELLIGENT WORLD.")).toBeVisible();
  await expect(page.getByRole("link", { name: /get protected/i }).first()).toBeVisible();
});

test("register page requires legal checkboxes", async ({ page }) => {
  await page.goto("/register");
  await expect(page.getByText("I agree to the")).toBeVisible();
  await expect(page.getByText("I acknowledge the")).toBeVisible();
});
