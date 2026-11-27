// Runs Lighthouse (accessibility, best practices, SEO) on the key screen of each
// use case while signed in. The browser is started by Playwright, the session
// token is written to localStorage, and Lighthouse then audits the page over
// the browser's debugging port without clearing that storage.
//
//   node lighthouse-run.mjs before      (or: after)
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { chromium } from '@playwright/test';
import lighthouse from 'lighthouse';
import desktopConfig from 'lighthouse/core/config/desktop-config.js';

const phase = process.argv[2] ?? 'before';
const UI = process.env.UI_URL ?? 'http://localhost:5173';
const API = process.env.API_URL ?? 'http://localhost:5001';
const PORT = 9333;
const out = path.join(import.meta.dirname, 'reports', 'lighthouse', phase);
fs.mkdirSync(out, { recursive: true });

const ACCOUNTS = {
  employee: { email: 'demo@leavedesk.in', password: 'demo1234' },
  admin: { email: 'admin@leavedesk.in', password: 'admin1234' },
};
const TARGETS = [
  { name: 'login', path: '/login', role: null },
  { name: 'my-leave', path: '/leave', role: 'employee' },
  { name: 'apply-dialog', path: '/leave?apply=1', role: 'employee' },
  { name: 'approvals', path: '/approvals', role: 'admin' },
];

async function tokenFor(role) {
  const reply = await fetch(`${API}/api/auth/login`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(ACCOUNTS[role]),
  });
  return (await reply.json()).access_token;
}

// A persistent context uses the browser's default profile, which is the one
// Lighthouse's own tab also uses, so the token written below is seen by the audit.
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'lh-profile-'));
const context = await chromium.launchPersistentContext(profile, { args: [`--remote-debugging-port=${PORT}`] });
const page = context.pages()[0] ?? (await context.newPage());
const summary = { phase, lighthouseVersion: null, chrome: context.browser()?.version(), screens: {} };

for (const target of TARGETS) {
  await page.goto(`${UI}/login`);
  await page.evaluate(([k, v]) => (v ? localStorage.setItem(k, v) : localStorage.removeItem(k)), [
    'leavedesk.token',
    target.role ? await tokenFor(target.role) : null,
  ]);

  const run = await lighthouse(
    `${UI}${target.path}`,
    {
      port: PORT,
      output: ['html', 'json'],
      logLevel: 'error',
      onlyCategories: ['accessibility', 'best-practices', 'seo'],
      disableStorageReset: true,
    },
    desktopConfig,
  );
  const [html, json] = run.report;
  fs.writeFileSync(path.join(out, `${target.name}.html`), html);
  fs.writeFileSync(path.join(out, `${target.name}.json`), json);

  const lhr = run.lhr;
  summary.lighthouseVersion = lhr.lighthouseVersion;
  summary.screens[target.name] = {
    url: lhr.finalDisplayedUrl,
    scores: Object.fromEntries(Object.entries(lhr.categories).map(([k, c]) => [k, Math.round(c.score * 100)])),
    failed: Object.values(lhr.audits)
      .filter((a) => a.score !== null && a.score < 1 && a.scoreDisplayMode !== 'informative' && a.scoreDisplayMode !== 'notApplicable')
      .map((a) => ({
        id: a.id,
        title: a.title,
        items: (a.details?.items ?? []).slice(0, 10).map((i) => i.node?.snippet ?? i.node?.selector ?? i.url ?? null).filter(Boolean),
      })),
  };
  console.log(target.name, JSON.stringify(summary.screens[target.name].scores));
}

fs.writeFileSync(path.join(out, 'summary.json'), JSON.stringify(summary, null, 2));
await context.close();
fs.rmSync(profile, { recursive: true, force: true });
