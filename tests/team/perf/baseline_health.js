// Calibration only, not one of the judged workloads: how fast does this machine answer the
// cheapest possible request (GET /api/health, no database, no login)? It shows the floor that
// every other number in performance.md sits on top of. BASELINE_SECONDS sets the length (default 30).
//
//   k6 run --summary-export=results/baseline_health.json baseline_health.js
import http from 'k6/http';
import { check } from 'k6';

const BASE = __ENV.BASE_URL || 'http://127.0.0.1:5001';

export const options = {
  vus: 1,
  duration: `${__ENV.BASELINE_SECONDS || 30}s`,
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  const reply = http.get(`${BASE}/api/health`);
  check(reply, { 'health answered 200': (r) => r.status === 200 });
}
