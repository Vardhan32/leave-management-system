import fs from 'node:fs';
import path from 'node:path';
import { test, expect } from '../../support/fixtures';
import { API_URL } from '../../support/api';

// Passive inspection of normal traffic: the browser opens the screens of both
// workflows and the test only reads what the server sends back (headers, cookies).
// It sends nothing a normal user would not send. The findings go to
// reports/security/passive_headers.json and are discussed in docs/team/security.md.

const WANTED = [
  'content-security-policy',
  'x-content-type-options',
  'x-frame-options',
  'referrer-policy',
  'strict-transport-security',
];
const OUT = path.join(__dirname, '..', '..', 'reports', 'security');

test.describe('Passive security controls', () => {
  test('PC-01 security headers and cookies on the UI and API responses', async ({ page, signIn }) => {
    await signIn('admin');
    const seen: { url: string; kind: string; status: number; headers: Record<string, string> }[] = [];
    page.on('response', (response) => {
      const url = new URL(response.url());
      const kind = url.pathname.startsWith('/api') ? 'api' : response.request().resourceType() === 'document' ? 'document' : 'asset';
      seen.push({ url: url.pathname, kind, status: response.status(), headers: response.headers() });
    });

    for (const route of ['/', '/leave', '/approvals']) {
      await page.goto(route);
      await page.waitForLoadState('networkidle');
    }

    const documents = seen.filter((r) => r.kind === 'document');
    const apis = seen.filter((r) => r.kind === 'api');
    expect(documents.length).toBeGreaterThan(0);
    expect(apis.length).toBeGreaterThan(0);

    const summary = (list: typeof seen) =>
      Object.fromEntries(WANTED.map((h) => [h, list.every((r) => h in r.headers) ? 'present' : 'missing']));
    const report = {
      checked: { documents: documents.length, api: apis.length },
      ui: summary(documents),
      api: summary(apis),
      setCookie: seen.filter((r) => 'set-cookie' in r.headers).length,
      serverHeaders: [...new Set(seen.map((r) => r.headers['server']).filter(Boolean))],
      localStorageKeys: await page.evaluate(() => Object.keys(window.localStorage)),
      cookiesInBrowser: (await page.context().cookies()).length,
    };
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, 'passive_headers.json'), JSON.stringify(report, null, 2));

    // control that holds: the app sets no cookies, so cookie attributes and CSRF do not apply
    expect(report.setCookie).toBe(0);
    expect(report.cookiesInBrowser).toBe(0);
    // control that holds: the session token is the only thing kept in localStorage
    expect(report.localStorageKeys).toEqual(['leavedesk.token']);
  });

  test('PC-02 CORS: a foreign origin gets no permission headers', async ({ api }) => {
    const foreign = await api.http.fetch(`${API_URL}/api/leave-types`, {
      headers: { Origin: 'http://untrusted.example', Authorization: `Bearer ${await api.token('employee')}` },
    });
    const allowed = await api.http.fetch(`${API_URL}/api/leave-types`, {
      headers: { Origin: 'http://localhost:5173', Authorization: `Bearer ${await api.token('employee')}` },
    });
    const result = {
      foreignOriginAllowOrigin: foreign.headers()['access-control-allow-origin'] ?? null,
      configuredOriginAllowOrigin: allowed.headers()['access-control-allow-origin'] ?? null,
    };
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, 'passive_cors.json'), JSON.stringify(result, null, 2));

    expect(result.foreignOriginAllowOrigin).toBeNull();
    expect(result.configuredOriginAllowOrigin).toBe('http://localhost:5173');
  });
});
