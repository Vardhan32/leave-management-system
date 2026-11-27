import { test, expect, findInQueue } from '../../support/fixtures';
import { workWindow } from '../../support/dates';
import { API_URL } from '../../support/api';
import { recordCheck, saveReply, shot } from '../../support/record';

// Access decisions from docs/team/access_matrix.md. Slots 36-41 are reserved for this file.
// Each test records role, action, expected, observed and evidence for the report.

test.describe('Access control', () => {
  test('AC-01 employee opens /approvals: denied, sent to the dashboard', { tag: ['@FR-10'] }, async ({ page, signIn }) => {
    await signIn('employee');
    await page.goto('/approvals');
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole('link', { name: 'Approvals' })).toHaveCount(0);
    recordCheck({
      id: 'AC-01', role: 'employee', action: 'open /approvals in the browser',
      expected: 'denied (redirect to /)', observed: `URL is ${new URL(page.url()).pathname}, no Approvals link in the menu`,
      evidence: await shot(page, 'AC-01'), pass: true,
    });
  });

  test('AC-02 employee opens /team: denied, sent to the dashboard', { tag: ['@FR-10'] }, async ({ page, signIn }) => {
    await signIn('employee');
    await page.goto('/team');
    await expect(page).toHaveURL(/\/$/);
    recordCheck({
      id: 'AC-02', role: 'employee', action: 'open /team in the browser',
      expected: 'denied (redirect to /)', observed: `URL is ${new URL(page.url()).pathname}`,
      evidence: await shot(page, 'AC-02'), pass: true,
    });
  });

  test('AC-03 employee calls the review endpoint: denied with 403', { tag: ['@FR-10', '@BR2'] }, async ({ api }) => {
    const w = workWindow(36, 1);
    const req = await api.create('employee', { type: 'CASUAL', start: w.start, end: w.end, reason: 'AC-03 employee tries to approve' });
    const reply = await api.call('employee', 'POST', `/api/leave-requests/${req.id}/review`, { decision: 'approve' });
    expect(reply.status).toBe(403);
    expect((await api.get('employee', req.id)).body.status).toBe('pending');
    recordCheck({
      id: 'AC-03', role: 'employee', action: `POST /api/leave-requests/${req.id}/review {approve} on own request`,
      expected: '403, request stays pending', observed: `${reply.status} "${reply.body.message}", request still pending`,
      evidence: saveReply('AC-03', `POST ${API_URL}/api/leave-requests/${req.id}/review`, reply), pass: true,
    });
  });

  test('AC-04 admin approves an employee request: allowed', { tag: ['@FR-07', '@BR2'] }, async ({ page, api, signIn }) => {
    const w = workWindow(37, 1);
    const reason = 'AC-04 admin approves';
    const req = await api.create('other', { type: 'CASUAL', start: w.start, end: w.end, reason });
    await signIn('admin');
    const row = await findInQueue(page, reason);
    await row.getByRole('button', { name: 'Review' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Approve' }).click();
    await expect(page.getByText(/request was approved/)).toBeVisible();
    const status = (await api.get('admin', req.id)).body.status;
    expect(status).toBe('approved');
    recordCheck({
      id: 'AC-04', role: 'admin', action: 'approve a pending request of another employee in the Approvals screen',
      expected: 'allowed, status becomes approved', observed: `status is ${status}`,
      evidence: await shot(page, 'AC-04'), pass: true,
    });
  });

  test('AC-05 admin approves their own request: denied with 403', { tag: ['@FR-10', '@BR2'] }, async ({ api }) => {
    const w = workWindow(38, 1);
    const req = await api.create('admin', { type: 'CASUAL', start: w.start, end: w.end, reason: 'AC-05 admin own request' });
    const reply = await api.review(req.id, 'approve');
    expect(reply.status).toBe(403);
    expect((await api.get('admin', req.id)).body.status).toBe('pending');
    recordCheck({
      id: 'AC-05', role: 'admin', action: `POST /api/leave-requests/${req.id}/review {approve} on the admin's own request`,
      expected: '403, request stays pending', observed: `${reply.status} "${reply.body.message}", request still pending`,
      evidence: saveReply('AC-05', `POST ${API_URL}/api/leave-requests/${req.id}/review`, reply), pass: true,
    });
  });

  test("AC-06 employee reads another employee's request: hidden with 404", { tag: ['@FR-12'] }, async ({ api }) => {
    const w = workWindow(39, 1);
    const req = await api.create('other', { type: 'CASUAL', start: w.start, end: w.end, reason: 'AC-06 private request' });
    const reply = await api.get('employee', req.id);
    expect(reply.status).toBe(404);
    expect(JSON.stringify(reply.body)).not.toContain('AC-06 private request');
    recordCheck({
      id: 'AC-06', role: 'employee', action: `GET /api/leave-requests/${req.id} (belongs to another employee)`,
      expected: '404 and no data from the request', observed: `${reply.status} "${reply.body.message}"`,
      evidence: saveReply('AC-06', `GET ${API_URL}/api/leave-requests/${req.id}`, reply), pass: true,
    });
  });

  test('AC-07 employee cancels their own pending request: allowed', { tag: ['@FR-11'] }, async ({ api }) => {
    const w = workWindow(40, 1);
    const req = await api.create('employee', { type: 'CASUAL', start: w.start, end: w.end, reason: 'AC-07 own request' });
    const reply = await api.cancel('employee', req.id);
    expect(reply.status).toBe(200);
    expect(reply.body.status).toBe('cancelled');
    recordCheck({
      id: 'AC-07', role: 'employee', action: `POST /api/leave-requests/${req.id}/cancel on own pending request`,
      expected: '200, status cancelled', observed: `${reply.status}, status ${reply.body.status}`,
      evidence: saveReply('AC-07', `POST ${API_URL}/api/leave-requests/${req.id}/cancel`, reply), pass: true,
    });
  });

  test("AC-08 employee cancels another employee's request: denied with 403", { tag: ['@FR-11', '@FR-12'] }, async ({ api }) => {
    const w = workWindow(41, 1);
    const req = await api.create('other', { type: 'CASUAL', start: w.start, end: w.end, reason: 'AC-08 not yours to cancel' });
    const reply = await api.cancel('employee', req.id);
    expect(reply.status).toBe(403);
    expect((await api.get('other', req.id)).body.status).toBe('pending');
    recordCheck({
      id: 'AC-08', role: 'employee', action: `POST /api/leave-requests/${req.id}/cancel on another employee's request`,
      expected: '403, request stays pending', observed: `${reply.status} "${reply.body.message}", request still pending`,
      evidence: saveReply('AC-08', `POST ${API_URL}/api/leave-requests/${req.id}/cancel`, reply), pass: true,
    });
  });

  test("AC-09 employee reads another employee's balances: denied with 403", { tag: ['@FR-12'] }, async ({ api }) => {
    const other = (await api.call('other', 'GET', '/api/auth/me')).body.user.id;
    const reply = await api.call('employee', 'GET', `/api/leave-balances?user_id=${other}`);
    expect(reply.status).toBe(403);
    recordCheck({
      id: 'AC-09', role: 'employee', action: `GET /api/leave-balances?user_id=${other} (another employee)`,
      expected: '403', observed: `${reply.status} "${reply.body.message}"`,
      evidence: saveReply('AC-09', `GET ${API_URL}/api/leave-balances?user_id=${other}`, reply), pass: true,
    });
  });

  test('AC-10 employee calls the admin team endpoint: denied with 403', { tag: ['@FR-10'] }, async ({ api }) => {
    const reply = await api.call('employee', 'GET', '/api/team');
    expect(reply.status).toBe(403);
    recordCheck({
      id: 'AC-10', role: 'employee', action: 'GET /api/team (admin directory)',
      expected: '403', observed: `${reply.status} "${reply.body.message}"`,
      evidence: saveReply('AC-10', `GET ${API_URL}/api/team`, reply), pass: true,
    });
  });

  test('AC-11 no session: the browser is sent to /login', { tag: ['@FR-12'] }, async ({ page }) => {
    await page.goto('/leave');
    await expect(page).toHaveURL(/\/login$/);
    recordCheck({
      id: 'AC-11', role: 'anonymous', action: 'open /leave without signing in',
      expected: 'denied (redirect to /login)', observed: `URL is ${new URL(page.url()).pathname}`,
      evidence: await shot(page, 'AC-11'), pass: true,
    });
  });

  test('AC-12 no token: the API answers 401', { tag: ['@FR-12'] }, async ({ api }) => {
    const reply = await api.raw('GET', '/api/leave-requests');
    expect(reply.status).toBe(401);
    recordCheck({
      id: 'AC-12', role: 'anonymous', action: 'GET /api/leave-requests without a token',
      expected: '401', observed: `${reply.status} "${reply.body.message}"`,
      evidence: saveReply('AC-12', `GET ${API_URL}/api/leave-requests`, reply), pass: true,
    });
  });

  test('AC-13 admin opens /approvals: allowed', { tag: ['@FR-10'] }, async ({ page, signIn }) => {
    await signIn('admin');
    await page.goto('/approvals');
    await expect(page.getByRole('heading', { name: 'Leave approvals' })).toBeVisible();
    recordCheck({
      id: 'AC-13', role: 'admin', action: 'open /approvals in the browser',
      expected: 'allowed', observed: `URL is ${new URL(page.url()).pathname}, heading "Leave approvals" shown`,
      evidence: await shot(page, 'AC-13'), pass: true,
    });
  });
});
