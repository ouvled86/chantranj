// k6 load-sanity: register + browse the learning path + read stats under load.
// Run:  k6 run -e BASE=http://localhost:8080 devops/loadtest/browse.js
// Target: p95 < 800ms for the read paths at 200 VUs (record numbers in docs).

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.BASE || 'http://localhost:8080';

export const options = {
  scenarios: {
    browse: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 50 },
        { duration: '1m', target: 200 },
        { duration: '1m', target: 200 },
        { duration: '30s', target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<800'],
  },
};

export default function () {
  const u = `load_${__VU}_${__ITER}_${Date.now()}`;
  const jar = http.cookieJar();

  const reg = http.post(
    `${BASE}/api/v1/auth/register`,
    JSON.stringify({ email: `${u}@load.dev`, username: u.slice(0, 20), password: 'Passw0rd1' }),
    { headers: { 'Content-Type': 'application/json' } },
  );
  check(reg, { 'registered': (r) => r.status === 201 });

  const csrf = (jar.cookiesForURL(BASE)['csrf_token'] || [''])[0];

  const path = http.get(`${BASE}/api/v1/learn/path`);
  check(path, { 'path 200': (r) => r.status === 200 });

  const stats = http.get(`${BASE}/api/v1/users/me/stats`);
  check(stats, { 'stats 200': (r) => r.status === 200 });

  // one write to exercise the DB + gamification path
  http.post(`${BASE}/api/v1/learn/items/kq-mate/complete`, null, {
    headers: { 'X-CSRF-Token': csrf },
  });

  sleep(1);
}
