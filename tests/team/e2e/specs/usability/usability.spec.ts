import type { Page } from '@playwright/test';
import { test, expect, openApplyDialog, fillApplyForm, submitApplyForm, findInQueue } from '../../support/fixtures';
import { workWindow } from '../../support/dates';
import { ACCOUNTS } from '../../support/api';

// Usability tests. Slots 28-35 are reserved for this file.
//
// U-01  W1 task test: sign in, open the apply screen, get a rule rejection, correct it, succeed.
// U-02  W2 task test: sign in as admin, open the queue, approve, see the confirmation.
// U-03  Keyboard-only run through the apply form.
// U-04/U-05  Focus management of the dialog (failed on the original build, pass after the fix).

async function activeName(page: Page): Promise<string> {
  return page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    if (!el) return 'none';
    const label = el.closest('label')?.querySelector('.field__label')?.textContent;
    if (label) return label.trim();
    return (el.getAttribute('aria-label') || el.textContent || el.tagName).trim();
  });
}

/** Press Tab until the focused control changes (a date input has several Tab stops). */
async function tabToNext(page: Page): Promise<string> {
  const start = await activeName(page);
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press('Tab');
    const now = await activeName(page);
    if (now !== start) return now;
  }
  throw new Error(`focus never left "${start}"`);
}

/**
 * Which order the browser's date input expects when digits are typed. It follows the
 * operating system's regional settings, so it is measured on a scratch input rather than assumed.
 */
async function dateOrder(page: Page): Promise<'mdy' | 'dmy'> {
  await page.evaluate(() => {
    const probe = document.createElement('input');
    probe.type = 'date';
    probe.id = 'order-probe';
    document.body.appendChild(probe);
    probe.focus();
  });
  await page.keyboard.type('12252027'); // 25 December 2027 only reads correctly in one order
  const value = await page.locator('#order-probe').inputValue();
  await page.evaluate(() => document.getElementById('order-probe')?.remove());
  return value === '2027-12-25' ? 'mdy' : 'dmy';
}

function typedDate(iso: string, order: 'mdy' | 'dmy'): string {
  const [y, m, d] = iso.split('-');
  return order === 'mdy' ? `${m}${d}${y}` : `${d}${m}${y}`;
}

test.describe('Usability', () => {
  test('U-01 apply task: rejected value, correction, success', { tag: ['@FR-01', '@FR-05', '@BR1'] }, async ({ page, api }) => {
    const tooLong = workWindow(28, 13);
    const fixed = workWindow(28, 5);

    // start at the sign-in form, as a new session would
    await page.goto('/login');
    await page.getByLabel('Work email').fill(ACCOUNTS.employee.email);
    await page.getByLabel('Password', { exact: true }).fill(ACCOUNTS.employee.password);
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Ananya');

    await page.getByRole('link', { name: 'My leave', exact: true }).click();
    await page.getByRole('button', { name: 'Request leave' }).click();

    // 13 casual days against a balance of 12
    await fillApplyForm(page, { type: 'Casual', start: tooLong.start, end: tooLong.end, reason: 'Long trip to visit family' });
    await submitApplyForm(page);
    const dialog = page.getByRole('dialog', { name: 'Request time off' });
    await expect(dialog.getByText(/Only 12 day\(s\) of Casual Leave remain for/)).toBeVisible();
    await expect(dialog.getByText(/Try a shorter range or another leave type/)).toBeVisible();
    expect(await api.find('employee', tooLong.start, tooLong.end)).toHaveLength(0);

    // correct the end date to 5 working days
    await dialog.getByLabel('End date').fill(fixed.end);
    await expect(dialog.getByText('5 working days selected')).toBeVisible();
    await submitApplyForm(page);

    await expect(page.getByText('Request sent. Your manager will review it shortly.')).toBeVisible();
    await api.trackByDates('employee', fixed.start, fixed.end);
    const saved = await api.find('employee', fixed.start, fixed.end);
    expect(saved).toHaveLength(1);
    expect(saved[0]).toMatchObject({ status: 'pending', days: 5 });
  });

  test('U-02 review task: admin approves and sees the confirmation', { tag: ['@FR-07'] }, async ({ page, api, signIn }) => {
    const w = workWindow(29, 2);
    const reason = 'U-02 approve from the queue';
    const req = await api.create('other', { type: 'CASUAL', start: w.start, end: w.end, reason });
    await signIn('admin');

    const row = await findInQueue(page, reason);
    await expect(row).toContainText(ACCOUNTS.other.name);
    await row.getByRole('button', { name: 'Review' }).click();
    const dialog = page.getByRole('dialog', { name: 'Review leave request' });
    await expect(dialog.getByText(/of casual leave left this year/i)).toBeVisible(); // balance context shown
    await dialog.getByRole('button', { name: 'Approve' }).click();

    await expect(page.getByText(`${ACCOUNTS.other.name}'s request was approved.`)).toBeVisible();
    expect((await api.get('admin', req.id)).body.status).toBe('approved');
  });

  test('U-03 keyboard: tab order through the apply form, submit with Enter', { tag: ['@FR-01'] }, async ({ page, api, signIn }) => {
    const w = workWindow(30, 2);
    await signIn('employee');
    await page.goto('/leave');
    const dates = await dateOrder(page);
    await openApplyDialog(page);

    const dialog = page.getByRole('dialog', { name: 'Request time off' });
    await dialog.getByLabel('Leave type').focus();
    const order: string[] = [await activeName(page)];

    // leave type: keep Casual, move on; start date: type the digits
    order.push(await tabToNext(page));
    await page.keyboard.type(typedDate(w.start, dates));
    order.push(await tabToNext(page));
    await page.keyboard.type(typedDate(w.end, dates));
    order.push(await tabToNext(page));
    await page.keyboard.type('Keyboard only request, U-03');
    order.push(await tabToNext(page));
    order.push(await tabToNext(page));

    // required fields come in order, and the submit button is reached last
    expect(order.slice(0, 4)).toEqual(['Leave type', 'Start date', 'End date', 'Reason']);
    expect(order.at(-1)).toBe('Send request');
    // the Cancel button sits between Reason and Send request in the page order
    expect(order).toEqual(['Leave type', 'Start date', 'End date', 'Reason', 'Cancel', 'Send request']);

    await page.keyboard.press('Enter');
    await expect(page.getByText('Request sent. Your manager will review it shortly.')).toBeVisible();

    await api.trackByDates('employee', w.start, w.end);
    const saved = await api.find('employee', w.start, w.end);
    expect(saved).toHaveLength(1);
    expect(saved[0]).toMatchObject({ status: 'pending', days: 2 });
  });

  // Finding A11Y-02 (docs/team/defects_area3.md): before the fix the dialog did not take focus when
  // it opened. This test failed on the original build (saved in reports/logs/) and passes after the fix.
  test('U-04 focus moves into the dialog when it opens', { tag: ['@FR-01'] }, async ({ page, signIn }) => {
    await signIn('employee');
    await openApplyDialog(page);
    const inside = await page.evaluate(() => !!document.activeElement?.closest('[role="dialog"]'));
    expect(inside).toBe(true);
  });

  // Finding A11Y-03: before the fix Tab left the dialog and walked through the page behind it.
  test('U-05 Tab stays inside the open dialog', { tag: ['@FR-01'] }, async ({ page, signIn }) => {
    await signIn('employee');
    await openApplyDialog(page);
    await page.getByRole('dialog').getByLabel('Reason').focus();
    for (let i = 0; i < 12; i++) await page.keyboard.press('Tab');
    const inside = await page.evaluate(() => !!document.activeElement?.closest('[role="dialog"]'));
    expect(inside).toBe(true);
  });
});
