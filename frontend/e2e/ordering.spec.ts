import { test, expect, type Page } from "@playwright/test";
const password = process.env.E2E_PASSWORD || "test-only-password-123";
async function login(page: Page) {
  await page.goto("/");
  await page
    .getByLabel("Username", { exact: true })
    .fill(process.env.E2E_USERNAME || "admin");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: /Open workspace/ }).click();
  await expect(
    page
      .locator(".toss-hero")
      .getByRole("heading", { name: "Crispy. Juicy. Drippy." }),
  ).toBeVisible();
}
async function cart(page: Page) {
  await expect(page.locator(".pos-layout")).toBeVisible();
  const mobile = page.getByRole("button", { name: /View order/ });
  if (await mobile.isVisible()) await mobile.click();
}

test("customize, persist a draft, send, update another device, and complete", async ({
  page,
  context,
}, testInfo) => {
  await login(page);
  await page
    .getByRole("button", { name: "Add Crispy Tenders", exact: true })
    .click();
  await page.getByRole("button", { name: /Add to order/ }).click();
  await expect(page.getByRole("alert")).toContainText("Choose");
  await page.getByLabel("2 pieces", { exact: false }).check();
  await page.getByLabel(/Cajun Mayo/).check();
  await page.getByLabel("Special instructions").fill("Less oil");
  await page.getByRole("button", { name: /Add to order/ }).click();
  await page
    .getByRole("button", { name: "Add Crispy Tenders", exact: true })
    .click();
  await page.getByLabel("4 pieces", { exact: false }).check();
  await page.getByRole("button", { name: /Add to order/ }).click();
  await cart(page);
  const customer = `E2E ${testInfo.project.name} ${Date.now()}`;
  await page.getByLabel("Customer / pickup name").fill(customer);
  await expect(page.locator(".total")).toContainText("₹377");
  await page.reload();
  await cart(page);
  await expect(page.getByLabel("Customer / pickup name")).toHaveValue(customer);
  const kitchen = await context.newPage();
  await kitchen.goto("/kitchen");
  await expect(
    kitchen.getByRole("heading", { name: "Kitchen board" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Send to Kitchen", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "The kitchen has your order" }),
  ).toBeVisible();
  const ticket = kitchen.locator(".ticket").filter({ hasText: customer });
  await expect(ticket).toBeVisible();
  await expect(ticket).toContainText("Less oil");
  await expect(ticket.locator(".ticket-item")).toHaveCount(2);
  await ticket.getByRole("button", { name: "Start preparing" }).click();
  await expect(ticket.getByText("Preparing", { exact: true })).toBeVisible();
  await ticket.getByRole("button", { name: "Mark ready" }).click();
  await page.getByRole("button", { name: "Track order" }).click();
  const tracked = page.locator(".ticket").filter({ hasText: customer });
  await expect(tracked).toContainText("Ready to collect");
  await tracked.getByRole("button", { name: "Complete pickup" }).click();
  await expect(tracked.getByText("Completed", { exact: true })).toBeVisible();
  await page.screenshot({
    path: `test-results/orders-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await kitchen.close();
});

test("unknown server outcome preserves the draft and retries one order", async ({
  page,
}, testInfo) => {
  await login(page);
  await page
    .getByRole("button", { name: "Add Cheese Fries", exact: true })
    .click();
  await page.getByRole("button", { name: /Add to order/ }).click();
  await cart(page);
  const customer = `Retry ${testInfo.project.name} ${Date.now()}`;
  await page.getByLabel("Customer / pickup name").fill(customer);
  let first = true;
  await page.route("**/api/orders", async (route) => {
    if (route.request().method() === "POST" && first) {
      first = false;
      await route.fetch();
      await route.abort("failed");
    } else await route.continue();
  });
  await page
    .getByRole("button", { name: "Send to Kitchen", exact: true })
    .click();
  await expect(
    page.getByText("Confirmation pending.", { exact: false }),
  ).toBeVisible();
  await expect(page.getByLabel("Customer / pickup name")).toHaveValue(customer);
  await page.reload();
  await cart(page);
  await page.getByRole("button", { name: "Retry confirmation" }).click();
  await expect(
    page.getByRole("heading", { name: "The kitchen has your order" }),
  ).toBeVisible();
  const result = await page.request.get(
    `/api/orders?q=${encodeURIComponent(customer)}`,
  );
  expect((await result.json()).length).toBe(1);
});
