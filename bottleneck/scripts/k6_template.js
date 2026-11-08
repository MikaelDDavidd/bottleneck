// Parametrized k6 load test for before/after measurements.
// Run ONLY against test/staging, never production.
//
// Environment variables:
//   BASE_URL     https://staging.example.com            (required)
//   ROUTES       JSON list of routes for each iteration (required), e.g.
//                [{"name":"list","method":"GET","path":"/api/items"},
//                 {"name":"sync","method":"POST","path":"/api/sync","body":{"since":"1970-01-01T00:00:00Z"}}]
//   AUTH_TOKEN   bearer token (optional). Or log in once with:
//   LOGIN_PATH   e.g. /api/auth/login, LOGIN_BODY JSON body, TOKEN_FIELD (default "token")
//   VUS          virtual users (default 5)
//   DURATION     e.g. 60s (default 60s)
//   SLEEP        seconds between iterations (default 1)
//
//   k6 run --summary-export result.json k6_template.js
import http from 'k6/http';
import { check, sleep, fail } from 'k6';

const BASE = __ENV.BASE_URL;
const ROUTES = JSON.parse(__ENV.ROUTES || '[]');

const thresholds = { http_req_failed: ['rate<0.01'] };
// One threshold per route forces k6 to print p50/p95 per route in the summary.
for (const r of ROUTES) thresholds[`http_req_duration{route:${r.name}}`] = ['p(95)>=0'];

export const options = {
  vus: parseInt(__ENV.VUS || '5', 10),
  duration: __ENV.DURATION || '60s',
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'max'],
  thresholds,
};

const JSON_HEADERS = { 'Content-Type': 'application/json' };

export function setup() {
  if (!BASE || ROUTES.length === 0) fail('BASE_URL and ROUTES are required');
  if (__ENV.AUTH_TOKEN) return { token: __ENV.AUTH_TOKEN };
  if (__ENV.LOGIN_PATH) {
    const res = http.post(`${BASE}${__ENV.LOGIN_PATH}`, __ENV.LOGIN_BODY || '{}', { headers: JSON_HEADERS });
    const token = res.json(__ENV.TOKEN_FIELD || 'token');
    if (!token) fail(`login failed with status ${res.status}`);
    return { token };
  }
  return { token: null };
}

export default function (data) {
  const headers = { ...JSON_HEADERS };
  if (data.token) headers.Authorization = `Bearer ${data.token}`;

  for (const r of ROUTES) {
    const params = { headers, tags: { route: r.name } };
    const url = `${BASE}${r.path}`;
    const res = (r.method || 'GET').toUpperCase() === 'GET'
      ? http.get(url, params)
      : http.request(r.method.toUpperCase(), url, JSON.stringify(r.body || {}), params);
    check(res, {
      [`${r.name} 2xx`]: (x) => x.status >= 200 && x.status < 300,
      [`${r.name} not rate limited`]: (x) => x.status !== 429,
    });
  }
  sleep(parseFloat(__ENV.SLEEP || '1'));
}
