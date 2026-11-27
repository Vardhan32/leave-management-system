import fs from 'node:fs';
import path from 'node:path';
import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';
import { test, expect } from '../../support/fixtures';

// Full axe-core scans of the key screen of every use case. The JSON goes to
// reports/axe/<phase>/ ; run once with AXE_PHASE=before and, after the fix,
// with AXE_PHASE=after. The scan itself does not fail the run: the findings
// are analysed in docs/team/accessibility.md.
const PHASE = process.env.AXE_PHASE ?? 'before';
const OUT = path.join(__dirname, '..', '..', 'reports', 'axe', PHASE);
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'];

async function scan(page: Page, name: string) {
  const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(
    path.join(OUT, `${name}.json`),
    JSON.stringify(
      {
        screen: name,
        url: results.url,
        axeVersion: results.testEngine.version,
        violations: results.violations,
        incomplete: results.incomplete.map((i) => ({ id: i.id, impact: i.impact, nodes: i.nodes.length })),
        passes: results.passes.length,
      },
      null,
      2,
    ),
  );
  console.log(`axe ${PHASE} ${name}: ${results.violations.length} violation rules, ${results.violations.reduce((n, v) => n + v.nodes.length, 0)} elements`);
  return results;
}

test.describe(`axe scans (${PHASE})`, () => {
  test('login screen', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
    await scan(page, 'login');
  });

  test('UC-01/UC-03 My leave page', async ({ page, signIn }) => {
    await signIn('employee');
    await page.goto('/leave');
    await expect(page.getByRole('heading', { name: 'My leave' })).toBeVisible();
    await expect(page.getByRole('row').nth(1)).toBeVisible();
    await scan(page, 'my-leave');
  });

  test('UC-01 apply dialog', async ({ page, signIn }) => {
    await signIn('employee');
    await page.goto('/leave');
    await page.getByRole('button', { name: 'Request leave' }).click();
    await expect(page.getByRole('dialog', { name: 'Request time off' })).toBeVisible();
    await scan(page, 'apply-dialog');
  });

  test('UC-03 request detail dialog', async ({ page, signIn }) => {
    await signIn('employee');
    await page.goto('/leave');
    await page.getByRole('button', { name: 'View' }).first().click();
    await expect(page.getByRole('dialog', { name: 'Leave request' })).toBeVisible();
    await scan(page, 'request-detail-dialog');
  });

  test('UC-02 approvals page', async ({ page, signIn }) => {
    await signIn('admin');
    await page.goto('/approvals');
    await expect(page.getByRole('heading', { name: 'Leave approvals' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Review' }).first()).toBeVisible();
    await scan(page, 'approvals');
  });

  test('UC-02 review dialog', async ({ page, signIn }) => {
    await signIn('admin');
    await page.goto('/approvals');
    await page.getByRole('button', { name: 'Review' }).first().click();
    await expect(page.getByRole('dialog', { name: 'Review leave request' })).toBeVisible();
    await scan(page, 'review-dialog');
  });
});
