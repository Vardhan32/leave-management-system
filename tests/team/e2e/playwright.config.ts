import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';

// The UI and the API are started by hand (see README.md). If they are not
// running, Playwright starts them; if they are, it reuses them.
const UI_URL = process.env.UI_URL ?? 'http://localhost:5173';
const ZAP_PROXY = process.env.ZAP_PROXY; // e.g. http://localhost:8080 for the passive scan run

const backendDir = path.resolve(__dirname, '../../../backend');
const frontendDir = path.resolve(__dirname, '../../../frontend');

export default defineConfig({
  testDir: './specs',
  outputDir: 'reports/artifacts',
  fullyParallel: false,
  workers: 1, // the app uses one SQLite file, so tests run one at a time
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 15_000 }, // the app and the laptop it runs on can be slow: lists load after a second API call
  reporter: [
    ['list'],
    ['html', { outputFolder: 'reports/html', open: 'never' }],
    ['json', { outputFile: 'reports/results.json' }],
  ],
  use: {
    ...devices['Desktop Chrome'],
    baseURL: UI_URL,
    locale: 'en-US',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    // --lang fixes the browser UI language, which decides the order of the month, day and
    // year parts of a date input (month/day/year); the keyboard test types digits in that order
    launchOptions: { args: ['--lang=en-US', ...(ZAP_PROXY ? ['--proxy-bypass-list=<-loopback>'] : [])] },
    ...(ZAP_PROXY ? { proxy: { server: ZAP_PROXY } } : {}),
  },
  projects: [
    { name: 'use-cases', testMatch: 'use-cases/**/*.spec.ts' },
    { name: 'usability', testMatch: 'usability/**/*.spec.ts' },
    { name: 'accessibility', testMatch: 'accessibility/**/*.spec.ts' },
    { name: 'security', testMatch: 'security/**/*.spec.ts' },
  ],
  webServer: [
    {
      command: 'npm run dev',
      cwd: frontendDir,
      // checked from this machine, so it stays on localhost even when UI_URL points at host.docker.internal
      url: 'http://localhost:5173',
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: 'python -m flask --app run:app run --port 5001',
      cwd: backendDir,
      url: 'http://127.0.0.1:5001/api/health', // checked from this machine, like the UI above
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
