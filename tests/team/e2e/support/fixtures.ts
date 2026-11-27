import { test as base, expect, type Page } from '@playwright/test';
import { LeaveApi, type Role } from './api';

const TOKEN_KEY = 'leavedesk.token';

type Fixtures = {
  api: LeaveApi;
  /** Sign in without going through the login form, then the test opens a page. */
  signIn: (role: Role) => Promise<void>;
};

export const test = base.extend<Fixtures>({
  api: async ({ playwright }, use) => {
    const http = await playwright.request.newContext();
    const api = new LeaveApi(http);
    await use(api);
    await api.cleanup();
    await http.dispose();
  },

  signIn: async ({ page, api }, use) => {
    await use(async (role: Role) => {
      const token = await api.token(role);
      await page.addInitScript(
        ([key, value]) => window.localStorage.setItem(key, value),
        [TOKEN_KEY, token],
      );
    });
  },
});

export { expect };

/** Opens the apply dialog from the My leave page. */
export async function openApplyDialog(page: Page) {
  await page.goto('/leave');
  await page.getByRole('button', { name: 'Request leave' }).click();
  const dialog = page.getByRole('dialog', { name: 'Request time off' });
  await expect(dialog).toBeVisible();
  return dialog;
}

/** Fills the apply form. Dates are ISO strings (YYYY-MM-DD). */
export async function fillApplyForm(
  page: Page,
  v: { type?: string; start?: string; end?: string; reason?: string },
) {
  const dialog = page.getByRole('dialog', { name: 'Request time off' });
  if (v.type) {
    // option text is "Casual Leave · 12 days a year"; pick by the leading name
    const option = dialog.getByLabel('Leave type').locator('option', { hasText: v.type });
    await dialog.getByLabel('Leave type').selectOption({ value: (await option.getAttribute('value'))! });
  }
  if (v.start !== undefined) await dialog.getByLabel('Start date').fill(v.start);
  if (v.end !== undefined) await dialog.getByLabel('End date').fill(v.end);
  if (v.reason !== undefined) await dialog.getByLabel('Reason').fill(v.reason);
}

export async function submitApplyForm(page: Page) {
  await page.getByRole('button', { name: 'Send request' }).click();
}

/** Looks a request up in the admin queue by a unique piece of its reason. */
export async function findInQueue(page: Page, reasonText: string, status = 'pending') {
  await page.goto(`/approvals?status=${status}`);
  await page.getByRole('searchbox', { name: 'Search leave requests' }).fill(reasonText);
  const row = page.getByRole('row').filter({ hasText: reasonText });
  await expect(row).toHaveCount(1);
  return row;
}
