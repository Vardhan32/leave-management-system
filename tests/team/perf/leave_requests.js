// k6 workload for POST /api/leave-requests (workflow W1, Apply for leave).
//
// One iteration = create a one-day request, then cancel it, so the data is
// the same after every iteration. Only the create call is judged; the cancel
// is counted separately. Every iteration uses a new weekday as its date, so if a
// cancel ever fails the leftover request cannot block the next create. Metrics carry the tags op:create / op:cancel and
// phase:warmup / phase:steady, and the thresholds look only at the steady phase.
//
// One scenario runs for WARMUP + STEADY seconds with a fixed number of users.
// The phase tag follows the elapsed test time, so the number of users never
// changes and no two virtual users ever share a user account or a date.
//
//   k6 run -e VUS=5 --summary-export=results/vus5_run1.json leave_requests.js
//
// Environment variables: VUS (1..8), BASE_URL, P95_MS, STEADY_SECONDS (default 60), DEBUG.

import http from 'k6/http';
import exec from 'k6/execution';
import { check, fail } from 'k6';

const BASE = __ENV.BASE_URL || 'http://127.0.0.1:5001';
const VUS = parseInt(__ENV.VUS || '1', 10);
const P95_MS = parseInt(__ENV.P95_MS || (VUS === 1 ? '500' : '1000'), 10);
const WARMUP_SECONDS = 10;
const STEADY_SECONDS = parseInt(__ENV.STEADY_SECONDS || '60', 10);

// seeded employees, one per virtual user, so two users never collide
const USERS = [
  'demo@leavedesk.in',
  'rohan.iyer@leavedesk.in',
  'kabir.shah@leavedesk.in',
  'isha.verma@leavedesk.in',
  'arjun.menon@leavedesk.in',
  'sneha.kulkarni@leavedesk.in',
  'vikram.singh@leavedesk.in',
  'priya.deshpande@leavedesk.in',
];

export const options = {
  scenarios: {
    load: { executor: 'constant-vus', vus: VUS, duration: `${WARMUP_SECONDS + STEADY_SECONDS}s`, exec: 'apply' },
  },
  thresholds: {
    'http_req_duration{op:create,phase:steady}': [`p(95)<${P95_MS}`],
    'http_req_failed{op:create,phase:steady}': ['rate<0.01'],
    'http_req_failed{op:cancel,phase:steady}': ['rate<0.01'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

const JSON_HEADERS = { 'Content-Type': 'application/json' };

export function setup() {
  if (VUS < 1 || VUS > USERS.length) fail(`VUS must be between 1 and ${USERS.length}`);

  const tokens = [];
  for (let i = 0; i < VUS; i++) {
    const login = http.post(`${BASE}/api/auth/login`, JSON.stringify({ email: USERS[i], password: 'demo1234' }), {
      headers: JSON_HEADERS,
      tags: { op: 'login' },
    });
    if (login.status !== 200) fail(`login failed for ${USERS[i]}: ${login.status}`);
    tokens.push(login.json('access_token'));
  }

  const types = http.get(`${BASE}/api/leave-types`, { headers: { Authorization: `Bearer ${tokens[0]}` }, tags: { op: 'setup' } });
  const casual = types.json('leave_types').find((t) => t.code === 'CASUAL');

  return { tokens, casualId: casual.id };
}

// the n-th weekday after Monday 3 March 2031 (n = 0 is that Monday)
function weekdayNumber(n) {
  const date = new Date(Date.UTC(2031, 2, 3));
  date.setUTCDate(date.getUTCDate() + Math.floor(n / 5) * 7 + (n % 5));
  return date.toISOString().slice(0, 10);
}

export function apply(data) {
  const index = exec.vu.idInTest - 1; // one user per virtual user
  const day = weekdayNumber(exec.vu.iterationInInstance); // a new date every iteration
  const phase = exec.instance.currentTestRunDuration < WARMUP_SECONDS * 1000 ? 'warmup' : 'steady';
  const auth = { Authorization: `Bearer ${data.tokens[index]}`, 'Content-Type': 'application/json' };

  const created = http.post(
    `${BASE}/api/leave-requests`,
    JSON.stringify({
      leave_type_id: data.casualId,
      start_date: day,
      end_date: day,
      reason: 'Load test request, one day of casual leave',
    }),
    { headers: auth, tags: { op: 'create', phase }, responseCallback: http.expectedStatuses(201) },
  );
  const ok = check(created, { 'create answered 201': (r) => r.status === 201 });
  if (!ok && __ENV.DEBUG) console.warn(`create failed: status=${created.status} body=${String(created.body).slice(0, 160)}`);

  if (ok) {
    const cancelled = http.post(`${BASE}/api/leave-requests/${created.json('id')}/cancel`, null, {
      headers: auth,
      tags: { op: 'cancel', phase },
      responseCallback: http.expectedStatuses(200),
    });
    const cancelOk = check(cancelled, { 'cancel answered 200': (r) => r.status === 200 });
    if (!cancelOk && __ENV.DEBUG) console.warn(`cancel failed: status=${cancelled.status} body=${String(cancelled.body).slice(0, 160)}`);
  }
}
