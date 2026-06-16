import { expect, test } from "@playwright/test";

test("core loop: map → search → card → compare", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Greater Tokyo Alpha Atlas")).toBeVisible();
  await expect(page.getByRole("link", { name: "発掘" })).toBeVisible();
  await expect(page.getByRole("link", { name: "比較" })).toBeVisible();
  await expect(page.getByText("Market Pulse")).toBeVisible();
  await page.getByRole("button", { name: "リスク" }).click();
  await expect(page.locator(".lens-tabs button.on")).toHaveText("リスク");
  await page.getByRole("button", { name: "再開発" }).click();
  await expect(page.locator(".lens-tabs button.on")).toHaveText("再開発");
  await page.getByRole("button", { name: "価格" }).click();

  // discovery screen ranks stations and can save a station to the watchlist
  await page.getByRole("link", { name: "発掘" }).click();
  await expect(page.getByRole("heading", { name: "発掘候補" })).toBeVisible();
  await page.locator(".opportunity-card").first().getByRole("button", { name: "ウォッチ" }).click();
  await expect(page.locator(".watchlist-card")).toContainText(/ウォッチリスト/);
  await expect(page.locator(".watchlist-card .chip")).toHaveCount(1);
  await page.getByRole("link", { name: "地図" }).click();

  // search opens the station card (DOM-driven; no canvas clicking)
  await page.getByLabel("駅名で検索").fill("中野");
  await page.locator(".search-hits button").first().click();
  await expect(page.getByRole("heading", { name: /中野/ })).toBeVisible();
  await expect(page.getByText("㎡単価（中央値）")).toBeVisible();
  await expect(page.getByText("投資メモ")).toBeVisible();
  await expect(page.getByText("市場マイクロ構造")).toBeVisible();

  // add to compare and navigate to compare screen
  await page.getByRole("button", { name: "比較に追加" }).click();
  await expect(page).toHaveURL(/compare/);

  // pick a second station so the radar renders
  await page.locator(".picker input").last().fill("高円寺");
  await page.locator(".picker .search-hits button").first().click();

  // verify the radar axis label is visible
  // exact match → only the radar axis tick, never proseFor sentences containing the phrase
  await expect(page.getByText("価格の勢い", { exact: true })).toBeVisible();
});
