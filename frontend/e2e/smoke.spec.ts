import { expect, test } from '@playwright/test';

/** Happy-path smoke against a live stack (dev :8080 or BASE_URL): register a
 *  fresh user, complete the first lesson, confirm the XP reward. */
test('register → complete first lesson → earn XP', async ({ page }) => {
  const u = `e2e${Date.now().toString(36)}`;

  await page.goto('/register');
  await page.locator('input[type="email"]').fill(`${u}@test.dev`);
  await page.getByPlaceholder(/letters/).fill(u);
  await page.getByPlaceholder(/chars/).fill('Passw0rd1');
  await page.getByRole('button', { name: 'Create account' }).click();

  await expect(page).toHaveURL(/\/learn$/);
  await expect(page.getByRole('heading', { name: /Board Vision/ })).toBeVisible();

  await page.getByRole('link', { name: /Mating with king & queen/ }).click();
  await expect(page).toHaveURL(/\/learn\/kq-mate/);

  const next = page.getByRole('button', { name: /Next/ });
  for (let i = 0; i < 14; i++) {
    if (await next.isEnabled().catch(() => false)) await next.click();
  }

  await expect(page.getByText(/\+\d+ XP/).first()).toBeVisible({ timeout: 10_000 });
});

test('login as a seeded user and reach the Play lobby', async ({ page }) => {
  await page.goto('/login');
  // identifier is the only non-password text input on the login card
  await page.locator('input:not([type="password"])').first().fill('magnus_dev');
  await page.locator('input[type="password"]').fill('Passw0rd1');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/learn$/);

  await page.getByRole('link', { name: 'Play' }).click();
  await expect(page).toHaveURL(/\/play$/);
  await expect(page.getByRole('button', { name: /Find an opponent/ })).toBeVisible();
});
