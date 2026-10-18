import { test, expect } from "@playwright/test";

test("TOSS menu, assets and cart fit the device", async ({
  page,
  context,
}, testInfo) => {
  const response = await context.request.post("/api/auth/login", {
    data: {
      username: process.env.E2E_USERNAME || "admin",
      password: process.env.E2E_PASSWORD || "test-only-password-123",
    },
  });
  expect(response.ok()).toBeTruthy();
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Add Crispy Chick", exact: true }),
  ).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  expect(await page.locator(".food-card").count()).toBeGreaterThanOrEqual(27);
  await expect(page.locator("html")).toHaveClass("dark");
  for (const asset of [
    "/images/toss-feast.png",
    "/images/toss-tenders.png",
    "/images/toss-wrap.png",
    "/fonts/anton.ttf",
  ]) {
    expect((await context.request.get(asset)).ok()).toBeTruthy();
  }
  await page.screenshot({
    path: `test-results/toss-final-${testInfo.project.name}.png`,
  });
  if (testInfo.project.name === "tablet") {
    await expect(page.locator(".brand .toss-logo")).toBeVisible();
    const sidebar = await page.locator(".sidebar").boundingBox();
    for (const icon of await page.locator(".sidebar nav a svg").all()) {
      const box = await icon.boundingBox();
      expect(box && sidebar && box.x >= sidebar.x).toBeTruthy();
      expect(box && sidebar && box.x + box.width <= sidebar.x + sidebar.width).toBeTruthy();
    }
    await expect(page.locator(".cart-pane")).toBeVisible();
    const box = await page
      .getByRole("button", { name: "Send to Kitchen", exact: true })
      .boundingBox();
    expect(box && box.y + box.height).toBeLessThanOrEqual(1180);
  }
  expect(errors).toEqual([]);
});
