import fs from 'node:fs';
import path from 'node:path';
import type { Page } from '@playwright/test';

// Every access check writes one entry (role, action, expected, observed, evidence)
// to reports/access/checks.json. A rerun replaces the entry with the same id.
const DIR = path.join(__dirname, '..', 'reports', 'access');
const FILE = path.join(DIR, 'checks.json');

export interface Check {
  id: string;
  role: string;
  action: string;
  expected: string;
  observed: string;
  evidence: string;
  pass: boolean;
}

export function recordCheck(entry: Check) {
  fs.mkdirSync(path.join(DIR, 'evidence'), { recursive: true });
  const all: Check[] = fs.existsSync(FILE) ? JSON.parse(fs.readFileSync(FILE, 'utf-8')) : [];
  const rest = all.filter((c) => c.id !== entry.id);
  rest.push(entry);
  rest.sort((a, b) => a.id.localeCompare(b.id));
  fs.writeFileSync(FILE, JSON.stringify(rest, null, 2));
}

/** Evidence for a browser check: a screenshot, returned as a repo-relative path. */
export async function shot(page: Page, id: string): Promise<string> {
  fs.mkdirSync(path.join(DIR, 'evidence'), { recursive: true });
  const file = path.join(DIR, 'evidence', `${id}.png`);
  await page.screenshot({ path: file });
  return `tests/team/e2e/reports/access/evidence/${id}.png`;
}

/** Evidence for an API check: the status and body, stored as JSON. */
export function saveReply(id: string, request: string, reply: { status: number; body: unknown }): string {
  fs.mkdirSync(path.join(DIR, 'evidence'), { recursive: true });
  fs.writeFileSync(path.join(DIR, 'evidence', `${id}.json`), JSON.stringify({ request, ...reply }, null, 2));
  return `tests/team/e2e/reports/access/evidence/${id}.json`;
}
