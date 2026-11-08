# Backend and server

Techniques 7 to 12.

## 7. Brotli or Gzip compression

**Detect.** `bash scripts/check_http.sh <api-url>`: it sends `Accept-Encoding: br, gzip` and shows
whether `content-encoding` comes back, plus the raw vs. compressed size. In code: `compression`
middleware (Express), `GZipMiddleware` (Django/FastAPI), `gzip on` (nginx), Traefik `compress`
middleware, Caddy `encode`. Check API responses, not only the HTML of the web app: it is common
for the frontend host to compress and the API not to.

**Evidence.** The response headers and sizes.

**Worth fixing when** JSON responses are more than a few KB and clients are on mobile or slow
networks. JSON usually shrinks 60 to 90%. Native HTTP clients (Dart `HttpClient`, OkHttp,
`URLSession`, browsers) send `Accept-Encoding` and decompress transparently, so clients rarely
need changes.
**Not worth it when** responses are tiny, or already compressed upstream (check the header, not
the config).

**Fix.** Compress at one layer only (app or proxy). Skip already-compressed content (images,
zip). Keep a size threshold (~1 KB). Avoid compressing secrets mixed with attacker-controlled
input on the same response (BREACH) if responses reflect user input next to tokens.

## 8. Cache in Redis for the most requested data

**Detect.** Repeated identical reads across users (catalog, plans, settings, reference lists),
and how much they cost. Check the database cache hit ratio first (`references/database.md`).

**Worth fixing when** the same expensive computation or query is served many times per minute and
its result changes rarely, or the database is CPU/IO bound.
**Not worth it when** the database already serves the data from memory quickly, traffic is low,
or the data is per-user and changes constantly. A cache adds invalidation bugs and another
service to run.

**Fix.** Start with in-process memoization or HTTP caching before a new service. If Redis: the
key must include the tenant/user for per-tenant data (otherwise one customer sees another's
data), set a TTL, and invalidate on write.

## 9. Queue for slow tasks

**Detect.** Request handlers that send emails, generate PDFs, call slow third parties, resize
images or process uploads before answering. Long p95 on endpoints that "do a lot".

**Worth fixing when** the slow work does not need to finish before the user gets an answer, or it
fails often and needs retries.
**Not worth it when** the work is quick, or the user needs the result right away (then make it
faster instead).

**Fix.** A job queue (BullMQ, Sidekiq, Celery, RQ, pg-boss/Graphile Worker if you only have
Postgres) with retries, idempotent jobs and a status the client can poll.

## 10. Timeouts on external APIs

**Detect.** HTTP calls without timeout: `axios` without `timeout`, `fetch` without
`AbortSignal.timeout`, Python `requests` without `timeout=`, SDK clients with defaults of minutes.
The scanner flags many of these; confirm each.

**Worth fixing when** any request path waits on a third party. Without a timeout, one slow
provider holds connections and workers until the whole API stalls.
**Not worth it when** every call already has a sane timeout (say where).

**Fix.** Explicit timeouts (connect + total), retries only for idempotent calls with backoff and
jitter, and a fallback or clear error for the user.

## 11. Parallel independent requests

**Detect.** Sequential awaits that do not depend on each other:
`const a = await x(); const b = await y();` where `y` does not use `a`. Same in the frontend
(waterfall in the network tab) and in mobile startup.

**Worth fixing when** two or more independent I/O calls sit on the slow path.
**Not worth it when** the calls share a small connection pool: firing 50 queries in parallel on a
pool of 10 only moves the queue. Batch or join instead.

**Fix.** `Promise.all` / `Promise.allSettled`, `asyncio.gather`, `Future.wait`, with a
concurrency limit when the list is large.

## 12. Multiple instances behind a load balancer

**Detect.** CPU saturation of a single process under the load test, single-threaded runtimes
(Node, Python) using one core on a multi-core host, deployment config.

**Worth fixing when** one process is CPU-bound and the host has idle cores (cluster mode / more
workers), or availability requires more than one instance.
**Not worth it when** the bottleneck is the database or the host has 1 to 2 cores shared with the
database: more instances fight for the same CPU.

**Fix.** Make the app stateless first (sessions, uploads and caches outside the process), then
add workers/instances. Socket.IO and other stateful protocols need sticky sessions or an adapter.
