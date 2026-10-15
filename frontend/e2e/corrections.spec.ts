import { test, expect } from "@playwright/test";

test("correct an active ticket, show kitchen changes, and cancel with a reason", async ({
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
  await page
    .getByRole("button", { name: "Add Cheese Fries", exact: true })
    .click();
  if (await page.getByRole("button", { name: /View order/ }).isVisible())
    await page.getByRole("button", { name: /View order/ }).click();
  const customer = `Correction ${Date.now()}`;
  await page.getByLabel("Customer / pickup name").fill(customer);
  await page
    .getByRole("button", { name: "Send to Kitchen", exact: true })
    .click();
  await page.getByRole("button", { name: "Track order" }).click();
  const kitchen = await context.newPage();
  await kitchen.goto("/kitchen");
  const ticket = kitchen.locator(".ticket").filter({ hasText: customer });
  await expect(ticket).toBeVisible();
  await page
    .locator(".ticket")
    .filter({ hasText: customer })
    .getByRole("button", { name: "Correct order" })
    .click();
  await page.getByRole("button", { name: "Increase Cheese Fries" }).click();
  await page.getByLabel("Reason for correction").fill("One more portion");
  await page
    .getByRole("button", { name: "Send correction", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Correction confirmed" }),
  ).toBeVisible();
  await expect(ticket.locator(".item-quantity")).toHaveText("2×");
  await ticket.getByRole("button", { name: "View", exact: true }).click();
  await kitchen.getByText("What changed", { exact: true }).click();
  await expect(
    kitchen.getByText("Before correction", { exact: true }),
  ).toBeVisible();
  await expect(
    kitchen.getByText("After correction", { exact: true }),
  ).toBeVisible();
  await kitchen.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("button", { name: "Track order" }).click();
  await page
    .locator(".ticket")
    .filter({ hasText: customer })
    .getByRole("button", { name: "Cancel", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Cancel order", exact: true }),
  ).toBeDisabled();
  await page.getByLabel("Cancellation reason").fill("Customer changed plans");
  await page.getByRole("button", { name: "Cancel order", exact: true }).click();
  await expect(
    page.locator(".ticket").filter({ hasText: customer }),
  ).toContainText("Cancelled");
  await expect(ticket).toHaveCount(0);
  await kitchen.close();
});
