import { test, expect, findInQueue } from '../../support/fixtures';
import { workWindow } from '../../support/dates';
import { ACCOUNTS } from '../../support/api';

// UC-02 Review a leave request (admin). Slots 10-19 are reserved for this file.
// Each test creates its own pending request through the API, then reviews it in the browser.
const NOTE = 'Checked against the team calendar.';

async function openReview(page: any, reason: string) {
  const row = await findInQueue(page, reason);
  await row.getByRole('button', { name: 'Review' }).click();
  const dialog = page.getByRole('dialog', { name: 'Review leave request' });
  await expect(dialog).toBeVisible();
  return dialog;
}

test.describe('UC-02 Review a leave request', () => {
  test.beforeEach(async ({ signIn }) => {
    await signIn('admin');
  });

  test('UC-02-M1 main: approve with a note', { tag: ['@FR-07', '@BR2', '@BR3'] }, async ({ page, api }) => {
    const w = workWindow(10, 2);
    const reason = 'UC-02 M1 approve with note';
    const req = await api.create('other', { type: 'CASUAL', start: w.start, end: w.end, reason });
    const usedBefore = await api.usedDays('other', 'CASUAL', w.year);

    const dialog = await openReview(page, reason);
    await dialog.getByLabel('Decision note').fill(NOTE);
    await dialog.getByRole('button', { name: 'Approve' }).click();

    await expect(page.getByText(`${ACCOUNTS.other.name}'s request was approved.`)).toBeVisible();

    const after = (await api.get('admin', req.id)).body;
    expect(after.status).toBe('approved');
    expect(after.review_note).toBe(NOTE);
    expect(after.reviewed_by.name).toBe(ACCOUNTS.admin.name);
    expect(await api.usedDays('other', 'CASUAL', w.year)).toBe(usedBefore + 2);
  });

  test('UC-02-A1 alternative: approve without a note', { tag: ['@FR-07'] }, async ({ page, api }) => {
    const w = workWindow(11, 1);
    const reason = 'UC-02 A1 approve no note';
    const req = await api.create('other', { type: 'SICK', start: w.start, end: w.end, reason });

    const dialog = await openReview(page, reason);
    await dialog.getByRole('button', { name: 'Approve' }).click();
    await expect(page.getByText(/request was approved/)).toBeVisible();

    const after = (await api.get('admin', req.id)).body;
    expect(after.status).toBe('approved');
    expect(after.review_note).toBeNull();
  });

  test('UC-02-A2 alternative: reject with a note, balance unchanged', { tag: ['@FR-08', '@BR3'] }, async ({ page, api }) => {
    const w = workWindow(12, 2);
    const reason = 'UC-02 A2 reject with note';
    const req = await api.create('other', { type: 'CASUAL', start: w.start, end: w.end, reason });
    const usedBefore = await api.usedDays('other', 'CASUAL', w.year);

    const dialog = await openReview(page, reason);
    await dialog.getByLabel('Decision note').fill('Release week, please pick another date.');
    await dialog.getByRole('button', { name: 'Reject' }).click();
    await expect(page.getByText(`${ACCOUNTS.other.name}'s request was rejected.`)).toBeVisible();

    const after = (await api.get('admin', req.id)).body;
    expect(after.status).toBe('rejected');
    expect(after.review_note).toContain('Release week');
    expect(await api.usedDays('other', 'CASUAL', w.year)).toBe(usedBefore);
  });

  test('UC-02-A3 alternative: the decided request moves to the Approved tab', { tag: ['@FR-07'] }, async ({ page, api }) => {
    const w = workWindow(13, 1);
    const reason = 'UC-02 A3 find in approved tab';
    await api.create('other', { type: 'CASUAL', start: w.start, end: w.end, reason });

    const dialog = await openReview(page, reason);
    await dialog.getByRole('button', { name: 'Approve' }).click();
    await expect(page.getByText(/request was approved/)).toBeVisible();

    await findInQueue(page, reason, 'approved'); // exactly one row in the Approved tab
    await page.goto('/approvals?status=pending');
    await page.getByRole('searchbox', { name: 'Search leave requests' }).fill(reason);
    await expect(page.getByText('No matches found')).toBeVisible();
  });

  test('UC-02-E1 exception: reject without a note', { tag: ['@FR-08', '@BR2'] }, async ({ page, api }) => {
    const w = workWindow(14, 1);
    const reason = 'UC-02 E1 reject without note';
    const req = await api.create('other', { type: 'CASUAL', start: w.start, end: w.end, reason });

    const dialog = await openReview(page, reason);
    await dialog.getByRole('button', { name: 'Reject' }).click();

    await expect(dialog.getByText('Add a short note before rejecting this request.')).toBeVisible();
    expect((await api.get('admin', req.id)).body.status).toBe('pending');
  });

  test('UC-02-E2 exception: approval would exceed the balance', { tag: ['@FR-09', '@BR1'] }, async ({ page, api }) => {
    const first = workWindow(15, 8);
    const second = workWindow(16, 8); // same year, so both draw on the same 12 casual days
    await api.create('other', { type: 'CASUAL', start: first.start, end: first.end, reason: 'UC-02 E2 first eight days' });
    const late = await api.create('other', { type: 'CASUAL', start: second.start, end: second.end, reason: 'UC-02 E2 second eight days' });

    const firstDialog = await openReview(page, 'UC-02 E2 first eight days');
    await firstDialog.getByRole('button', { name: 'Approve' }).click();
    await expect(page.getByText(/request was approved/)).toBeVisible();
    const used = await api.usedDays('other', 'CASUAL', first.year);
    expect(used).toBe(8);

    // 8 + 8 is more than 12: the server refuses the second approval
    const dialog = await openReview(page, 'UC-02 E2 second eight days');
    await dialog.getByRole('button', { name: 'Approve' }).click();
    await expect(dialog.getByText('This request exceeds the available balance.')).toBeVisible();

    expect((await api.get('admin', late.id)).body.status).toBe('pending');
    expect(await api.usedDays('other', 'CASUAL', first.year)).toBe(used);
  });

  // Defect DEF-A3-01: the review dialog loads the balance of the current year, so for a request
  // in another year it neither warns nor disables Approve.
  test('UC-02-D1 known defect: the dialog warns when the request year has too few days left', { tag: ['@FR-09'] }, async ({ page, api }) => {
    test.fail(process.env.DEF_A3_01_FIXED !== '1', "DEF-A3-01: review dialog uses this year's balance");
    const first = workWindow(15, 8);
    const second = workWindow(16, 8);
    await api.create('other', { type: 'CASUAL', start: first.start, end: first.end, reason: 'UC-02 D1 first eight days' });
    await api.create('other', { type: 'CASUAL', start: second.start, end: second.end, reason: 'UC-02 D1 second eight days' });
    const firstDialog = await openReview(page, 'UC-02 D1 first eight days');
    await firstDialog.getByRole('button', { name: 'Approve' }).click();
    await expect(page.getByText(/request was approved/)).toBeVisible();

    const dialog = await openReview(page, 'UC-02 D1 second eight days');
    await expect(dialog.getByText(/needs 8 days, but only 4 days remain/)).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'Approve' })).toBeDisabled();
  });

  test('UC-02-E3 exception: the request was already decided', { tag: ['@FR-10', '@BR3'] }, async ({ page, api }) => {
    const w = workWindow(17, 1);
    const reason = 'UC-02 E3 decided meanwhile';
    const req = await api.create('other', { type: 'CASUAL', start: w.start, end: w.end, reason });

    const dialog = await openReview(page, reason);
    await api.cancel('other', req.id); // the employee withdraws it while the dialog is open
    await dialog.getByRole('button', { name: 'Approve' }).click();

    await expect(dialog.getByText('Only pending requests can be reviewed.')).toBeVisible();
    expect((await api.get('admin', req.id)).body.status).toBe('cancelled');
    expect(await api.usedDays('other', 'CASUAL', w.year)).toBe(0);
  });

  test('UC-02-E4 exception: an admin cannot review their own request', { tag: ['@FR-10', '@BR2'] }, async ({ page, api }) => {
    const w = workWindow(18, 1);
    const reason = 'UC-02 E4 own request';
    const req = await api.create('admin', { type: 'CASUAL', start: w.start, end: w.end, reason });

    const dialog = await openReview(page, reason);
    await dialog.getByRole('button', { name: 'Approve' }).click();

    await expect(dialog.getByText('You cannot review your own leave request.')).toBeVisible();
    expect((await api.get('admin', req.id)).body.status).toBe('pending');
    expect(await api.usedDays('admin', 'CASUAL', w.year)).toBe(0);
  });
});
