import { test, expect, openApplyDialog, fillApplyForm, submitApplyForm } from '../../support/fixtures';
import { workWindow, weekendWindow, yesterday } from '../../support/dates';

// UC-01 Apply for leave (employee). Flow ids match docs/team/use_cases/UC-01.md.
// Slots 0-9 are reserved for this file so its dates never meet another test's.
const REASON = 'Family event out of town, UC-01';

test.describe('UC-01 Apply for leave', () => {
  test.beforeEach(async ({ signIn }) => {
    await signIn('employee');
  });

  test('UC-01-M1 main: apply for 2 casual days', { tag: ['@FR-01', '@FR-02', '@BR1'] }, async ({ page, api }) => {
    const w = workWindow(0, 2);
    const usedBefore = await api.usedDays('employee', 'CASUAL', w.year);

    await openApplyDialog(page);
    await fillApplyForm(page, { type: 'Casual', start: w.start, end: w.end, reason: REASON + ' M1' });
    await expect(page.getByText('2 working days selected')).toBeVisible();
    await submitApplyForm(page);

    await expect(page.getByText('Request sent. Your manager will review it shortly.')).toBeVisible();
    await expect(page.getByRole('dialog')).toHaveCount(0);

    // postcondition: one pending request, 2 days, and the balance is untouched
    await api.trackByDates('employee', w.start, w.end);
    const found = await api.find('employee', w.start, w.end);
    expect(found).toHaveLength(1);
    expect(found[0]).toMatchObject({ status: 'pending', days: 2 });
    expect(await api.usedDays('employee', 'CASUAL', w.year)).toBe(usedBefore);
  });

  test('UC-01-A1 alternative: another leave type (earned)', { tag: ['@FR-01'] }, async ({ page, api }) => {
    const w = workWindow(1, 3);
    await openApplyDialog(page);
    await fillApplyForm(page, { type: 'Earned', start: w.start, end: w.end, reason: REASON + ' A1' });
    await submitApplyForm(page);
    await expect(page.getByText('Request sent.')).toBeVisible();

    await api.trackByDates('employee', w.start, w.end);
    const found = await api.find('employee', w.start, w.end);
    expect(found).toHaveLength(1);
    expect(found[0].leave_type.code).toBe('EARNED');
    expect(found[0].days).toBe(3);
  });

  test('UC-01-A2 alternative: a range over a weekend counts weekdays only', { tag: ['@FR-01', '@BR1'] }, async ({ page, api }) => {
    const w = weekendWindow(2); // Friday to Monday
    await openApplyDialog(page);
    await fillApplyForm(page, { type: 'Casual', start: w.start, end: w.end, reason: REASON + ' A2' });
    await expect(page.getByText('2 working days selected')).toBeVisible();
    await submitApplyForm(page);
    await expect(page.getByText('Request sent.')).toBeVisible();

    await api.trackByDates('employee', w.start, w.end);
    const found = await api.find('employee', w.start, w.end);
    expect(found[0].days).toBe(2);
  });

  test('UC-01-A3 alternative: open the form from the "Plan a break" link', { tag: ['@FR-01'] }, async ({ page, api }) => {
    const w = workWindow(3, 1);
    await page.goto('/leave');
    await page.getByRole('link', { name: 'Plan a break' }).click();
    await expect(page.getByRole('dialog', { name: 'Request time off' })).toBeVisible();

    await fillApplyForm(page, { type: 'Sick', start: w.start, end: w.end, reason: REASON + ' A3' });
    await submitApplyForm(page);
    await expect(page.getByText('Request sent.')).toBeVisible();

    await api.trackByDates('employee', w.start, w.end);
    expect((await api.find('employee', w.start, w.end))[0].leave_type.code).toBe('SICK');
  });

  test('UC-01-E1 exception: end date before start date', { tag: ['@FR-03'] }, async ({ page, api }) => {
    const w = workWindow(4, 3);
    await openApplyDialog(page);
    await fillApplyForm(page, { type: 'Casual', start: w.end, end: w.start, reason: REASON + ' E1' });
    await submitApplyForm(page);

    await expect(page.getByText('The end date cannot be before the start date.')).toBeVisible();
    await expect(page.getByRole('dialog')).toBeVisible();
    expect(await api.find('employee', w.end, w.start)).toHaveLength(0);
  });

  test('UC-01-E2 exception: reason shorter than 10 characters', { tag: ['@FR-02'] }, async ({ page, api }) => {
    const w = workWindow(5, 1);
    await openApplyDialog(page);
    await fillApplyForm(page, { type: 'Casual', start: w.start, end: w.end, reason: 'short' });
    await submitApplyForm(page);

    await expect(page.getByText('Add a little more detail (at least 10 characters).')).toBeVisible();
    expect(await api.find('employee', w.start, w.end)).toHaveLength(0);
  });

  test('UC-01-E3 exception: more days than the balance', { tag: ['@FR-05', '@BR1'] }, async ({ page, api }) => {
    const w = workWindow(6, 13); // casual allows 12 a year
    await openApplyDialog(page);
    await fillApplyForm(page, { type: 'Casual', start: w.start, end: w.end, reason: REASON + ' E3' });
    await expect(page.getByText(/needs 13 days, but you only have \d+ days/)).toBeVisible();
    await submitApplyForm(page);

    await expect(page.getByText(/Only 12 day\(s\) of Casual Leave remain for/)).toBeVisible();
    expect(await api.find('employee', w.start, w.end)).toHaveLength(0);
  });

  test('UC-01-E4 exception: dates overlap an existing request', { tag: ['@FR-04', '@BR4'] }, async ({ page, api }) => {
    const w = workWindow(7, 2);
    await api.create('employee', { type: 'CASUAL', start: w.start, end: w.end, reason: REASON + ' E4 first' });

    await openApplyDialog(page);
    await fillApplyForm(page, { type: 'Casual', start: w.start, end: w.end, reason: REASON + ' E4 second' });
    await submitApplyForm(page);

    await expect(page.getByText('You already have a pending or approved request that overlaps these dates.')).toBeVisible();
    expect(await api.find('employee', w.start, w.end)).toHaveLength(1); // no duplicate
  });

  test('UC-01-E5 exception: start date in the past', { tag: ['@FR-03'] }, async ({ page, api }) => {
    const past = yesterday();
    await openApplyDialog(page);
    await fillApplyForm(page, { type: 'Casual', start: past, end: past, reason: REASON + ' E5' });
    await submitApplyForm(page);

    // the form does not check this itself; the server does and the screen shows its message
    await expect(page.getByText('Leave cannot start in the past.')).toBeVisible();
    const mine = await api.requestsInYear('employee', Number(past.slice(0, 4)));
    expect(mine.filter((r) => r.reason.includes('UC-01 E5'))).toHaveLength(0);
  });

  // Defect DEF-A3-01: the balance hint in the dialog is the current year's balance,
  // not the balance of the year the dates fall in (see docs/team/accessibility.md, usability notes).
  test('UC-01-D1 known defect: the balance hint uses the year of the chosen dates', { tag: ['@FR-05'] }, async ({ page }) => {
    test.fail(process.env.DEF_A3_01_FIXED !== '1', "DEF-A3-01: hint shows this year's balance for a request in another year");
    const w = workWindow(8, 13);
    await openApplyDialog(page);
    await fillApplyForm(page, { type: 'Casual', start: w.start, end: w.end, reason: REASON + ' D1' });
    await expect(page.getByText(/needs 13 days, but you only have 12 days/)).toBeVisible();
  });
});
