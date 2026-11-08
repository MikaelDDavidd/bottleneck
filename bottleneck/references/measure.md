# Measurement

Techniques 29 to 31, plus how to run the before/after load test.

## 29. Trace slow requests (OpenTelemetry)

**Detect.** Any tracing/APM (OpenTelemetry SDK, Sentry performance, Datadog, New Relic), request
duration logging middleware, slow query logs.

**Worth fixing when** there are several services or external calls and nobody can say where a
slow request spends its time.
**Not worth it when** it is a single API with one database: a request-duration log plus the
database slow query log (`log_min_duration_statement`) and `pg_stat_statements` answer the same
question with far less setup. Recommend visibility proportional to the system.

**Fix.** Start with a middleware that logs method, route, status and duration, and alerts when
p95 of a window passes a threshold. Add OpenTelemetry auto-instrumentation when there are
multiple services.

## 30. Real user monitoring (RUM)

**Detect.** Field data collection: `web-vitals` library, analytics with Core Web Vitals, Firebase
Performance Monitoring, Sentry mobile performance, custom timing events (sync duration, screen
load) sent to logs.

**Worth fixing when** lab tests and real users disagree, or users are on networks/devices the
team does not test on (rural 3G, old Android phones).
**Not worth it when** the audience is small and internal and can be observed directly.

**Fix.** Web: report LCP, INP and CLS with `web-vitals` to an endpoint or analytics. Mobile:
measure the slow flows (startup, sync, main lists) with timestamps and network type, and send
them with the existing logging.

## 31. Test on a real phone and a slow network

**Detect.** Whether anyone tested on a mid/low-end device and throttled network: Chrome DevTools
network throttling and CPU slowdown, Lighthouse mobile profile, iOS Network Link Conditioner,
Android emulator network speed, real device on 3G.

**Worth fixing when** end users are mobile, rural, or on old devices.
**Not worth it when** the product is a desktop-only internal tool on office networks.

## Load test with k6 (before/after)

`scripts/k6_template.js` is a parametrized k6 script: it logs in once in `setup()` (credentials
from environment variables), then each virtual user loops over the routes you list, tagging each
route so the summary shows p50/p95 per route.

```bash
BASE_URL=https://staging.example.com \
ROUTES='[{"name":"list","method":"GET","path":"/api/items"},{"name":"sync","method":"POST","path":"/api/sync/pull","body":{"since":"1970-01-01T00:00:00Z"}}]' \
AUTH_TOKEN=... VUS=10 DURATION=60s \
k6 run --summary-export result-10.json scripts/k6_template.js
```

Method:
1. Run levels 1, 5, 10, 25, 50 virtual users, 60 s each, with a pause between levels.
2. Measure two scenarios when the slow path has a cheap and an expensive variant (full vs.
   incremental sync, empty vs. full cart).
3. Watch for `429` (rate limiter) and treat those levels as invalid, not as slowness.
4. Poll the production health endpoint during the run if staging shares infrastructure, and stop
   if it degrades.
5. Record date, time, origin of the load and environment next to the numbers. Re-run the exact
   same commands after each change.
