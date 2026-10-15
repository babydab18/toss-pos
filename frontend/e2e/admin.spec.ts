import { test, expect } from "@playwright/test";

test("manage a menu item, broadcast changes, and show responsive themes", async ({
  page,
  context,
}, testInfo) => {
  await page.goto("/");
  await page
    .getByLabel("Username", { exact: true })
    .fill(process.env.E2E_USERNAME || "admin");
  await page
    .getByLabel("Password", { exact: true })
    .fill(process.env.E2E_PASSWORD || "test-only-password-123");
  await page.getByRole("button", { name: /Open workspace/ }).click();
  await expect(
    page
      .locator(".toss-hero")
      .getByRole("heading", { name: "Crispy. Juicy. Drippy." }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
  await page.screenshot({
    path: `test-results/pos-${testInfo.project.name}.png`,
    fullPage: true,
  });
  if (testInfo.project.name === "mobile")
    await page.getByRole("button", { name: "Toggle theme" }).click();
  else await page.getByRole("button", { name: "Light mode" }).click();
  await expect(page.locator("html")).not.toHaveClass("dark");
  await page.screenshot({
    path: `test-results/dark-${testInfo.project.name}.png`,
    fullPage: true,
  });
  const secondDevice = await context.newPage();
  await secondDevice.goto("/");
  await page.getByRole("link", { name: "Menu & team" }).click();
  await page.getByRole("button", { name: "Add item", exact: true }).click();
  const name = `Test Kulfi ${testInfo.project.name} ${Date.now()}`;
  await page.getByLabel("Name", { exact: true }).fill(name);
  await page
    .getByLabel("Description / combo contents")
    .fill("Cardamom and pistachio");
  await page.getByLabel("Price (₹)").fill("75.50");
  await page.getByRole("button", { name: "Save changes" }).click();
  const card = secondDevice.getByRole("button", {
    name: `Add ${name}`,
    exact: true,
  });
  await expect(card).toBeVisible();
  await expect(card).toContainText("₹75.50");
  const row = page.locator(".admin-row").filter({ hasText: name });
  await row.getByRole("button", { name: "Available", exact: true }).click();
  await expect(card).toBeDisabled();
  await row.getByRole("button", { name: `Delete ${name}` }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Delete", exact: true })
    .click();
  await expect(card).toHaveCount(0);
  await page.getByRole("link", { name: "Overview" }).click();
  await expect(
    page.getByRole("heading", { name: "The daily overview" }),
  ).toBeVisible();
  await expect(
    page.getByText("Value of completed orders", { exact: true }),
  ).toBeVisible();
  await secondDevice.close();
});

test("reconnects and reloads changed orders after a network interruption", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await page
    .getByLabel("Username", { exact: true })
    .fill(process.env.E2E_USERNAME || "admin");
  await page
    .getByLabel("Password", { exact: true })
    .fill(process.env.E2E_PASSWORD || "test-only-password-123");
  await page.getByRole("button", { name: /Open workspace/ }).click();
  await expect(page.getByText("Live & connected")).toBeVisible();
  const menu = await (await page.request.get("/api/menu")).json();
  const item = menu.items.find(
    (i: { name: string }) => i.name === "Cheese Fries",
  );
  await page.getByRole("link", { name: "Kitchen", exact: true }).click();
  await context.setOffline(true);
  await expect(page.getByText("Offline · draft only")).toBeVisible();
  const customer = `Reconnect ${Date.now()}`;
  const created = await page.request.post("/api/orders", {
    headers: { "Idempotency-Key": `reconnect-${Date.now()}-order` },
    data: { customer, items: [{ menu_item_id: item.id, quantity: 1 }] },
  });
  expect(created.ok()).toBeTruthy();
  await context.setOffline(false);
  await expect(page.getByText("Live & connected")).toBeVisible({
    timeout: 20000,
  });
  await expect(
    page.locator(".ticket").filter({ hasText: customer }),
  ).toBeVisible();
});
