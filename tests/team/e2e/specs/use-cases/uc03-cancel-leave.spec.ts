import { test, expect } from '../../support/fixtures';
import { workWindow, uiRange } from '../../support/dates';

// UC-03 Cancel leave (employee). Slots 20-27 are reserved for this file.

async function openRequest(page: any, start: string, end: string, tab?: string) {
  await page.goto('/leave');
  if (tab) await page.getByRole('tab', { name: tab }).click(); // the list shows 6 rows a page
  const row = page.getByRole('row').filter({ hasText: uiRange(start, end) });
  await expect(row).toHaveCount(1);
  await row.getByRole('button', { name: 'View' }).click();
  const dialog = page.getByRole('dialog', { name: 'Leave request' });
  await expect(dialog).toBeVisible();
  return dialog;
}

test.describe('UC-03 Cancel leave', () => {
  test.beforeEach(async ({ signIn }) => {
    await signIn('employee');
  });

  test('UC-03-M1 main: withdraw a pending request', { tag: ['@FR-11', '@BR3'] }, async ({ page, api }) => {
    const w = workWindow(20, 2);
    const req = await api.create('employee', { type: 'CASUAL', start: w.start, end: w.end, reason: 'UC-03 M1 withdraw pending' });

    const dialog = await openRequest(page, w.start, w.end);
    await dialog.getByRole('button', { name: 'Cancel request' }).click();
    await page.getByRole('button', { name: 'Yes, cancel request' }).click();

    await expect(page.getByText('Request withdrawn. You can apply again any time.')).toBeVisible();
    expect((await api.get('employee', req.id)).body.status).toBe('cancelled');
    expect(await api.usedDays('employee', 'CASUAL', w.year)).toBe(0);
  });

  test('UC-03-A1 alternative: cancel approved leave, days return', { tag: ['@FR-11', '@BR3'] }, async ({ page, api }) => {
    const w = workWindow(21, 3);
    const req = await api.create('employee', { type: 'EARNED', start: w.start, end: w.end, reason: 'UC-03 A1 cancel approved' });
    await api.review(req.id, 'approve');
    expect(await api.usedDays('employee', 'EARNED', w.year)).toBe(3);

    const dialog = await openRequest(page, w.start, w.end);
    await dialog.getByRole('button', { name: 'Cancel request' }).click();
    await page.getByRole('button', { name: 'Yes, cancel request' }).click();

    await expect(page.getByText('Request cancelled. Those days are back in your balance.')).toBeVisible();
    expect((await api.get('employee', req.id)).body.status).toBe('cancelled');
    expect(await api.usedDays('employee', 'EARNED', w.year)).toBe(0);
  });

  test('UC-03-A2 alternative: "Keep it" leaves the request unchanged', { tag: ['@FR-11'] }, async ({ page, api }) => {
    const w = workWindow(22, 1);
    const req = await api.create('employee', { type: 'CASUAL', start: w.start, end: w.end, reason: 'UC-03 A2 keep it' });

    const dialog = await openRequest(page, w.start, w.end);
    await dialog.getByRole('button', { name: 'Cancel request' }).click();
    await page.getByRole('button', { name: 'Keep it' }).click();

    await expect(page.getByRole('dialog')).toHaveCount(0);
    expect((await api.get('employee', req.id)).body.status).toBe('pending');
  });

  test('UC-03-E1 exception: leave that already started', { tag: ['@FR-11', '@BR3'] }, async ({ page, api }) => {
    // the seed holds an approved casual request for the demo user that ended in the past
    const past = (await api.requestsInYear('employee', new Date().getFullYear())).find(
      (r) => r.status === 'approved' && r.end_date < new Date().toISOString().slice(0, 10),
    );
    expect(past, 'seed should contain a past approved request').toBeTruthy();

    const dialog = await openRequest(page, past.start_date, past.end_date, 'Approved');
    await expect(dialog.getByRole('button', { name: 'Cancel request' })).toHaveCount(0);

    const direct = await api.cancel('employee', past.id); // the server refuses it too
    expect(direct.status).toBe(409);
    expect(direct.body.message).toBe('Leave that has already started cannot be cancelled.');
    expect((await api.get('employee', past.id)).body.status).toBe('approved');
  });

  test('UC-03-E2 exception: a rejected request cannot be cancelled', { tag: ['@FR-11', '@BR3'] }, async ({ page, api }) => {
    const w = workWindow(23, 1);
    const req = await api.create('employee', { type: 'CASUAL', start: w.start, end: w.end, reason: 'UC-03 E2 rejected' });
    await api.review(req.id, 'reject', 'Not possible that week.');

    const dialog = await openRequest(page, w.start, w.end);
    await expect(dialog.getByRole('button', { name: 'Cancel request' })).toHaveCount(0);

    const direct = await api.cancel('employee', req.id);
    expect(direct.status).toBe(409);
    expect((await api.get('employee', req.id)).body.status).toBe('rejected');
  });
});
