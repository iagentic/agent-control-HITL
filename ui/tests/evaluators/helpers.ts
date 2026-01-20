/**
 * Shared helpers for evaluator tests
 */

import { expect, type Page } from "@playwright/test";

const AGENT_URL = "/agents/agent-1";

/**
 * Opens the control store and selects a plugin to create a new control
 */
export async function openEvaluatorForm(page: Page, pluginName: string) {
  await page.goto(AGENT_URL);

  // Open control store modal
  await page.getByTestId("add-control-button").first().click();
  await expect(page.getByRole("heading", { name: "Control store" })).toBeVisible();

  // Find and click Add button for the plugin
  const pluginRow = page.locator("tr", { hasText: pluginName });
  await pluginRow.getByRole("button", { name: "Add" }).click();

  // Wait for the create control modal
  await expect(page.getByRole("heading", { name: "Create Control" })).toBeVisible();
}

