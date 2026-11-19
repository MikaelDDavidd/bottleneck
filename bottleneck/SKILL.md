---
name: bottleneck
description: Performance audit for real systems (APIs, databases, web frontends and mobile apps). Finds where an app is actually slow, checks 31 techniques against the code and the live system with evidence (curl headers, EXPLAIN, N+1 scans, bundle sizes, load tests), gives a verdict per technique (done, worth fixing, not worth it at this scale, not applicable) and returns a prioritized plan with before/after measurement. Use this skill whenever someone asks why their app, API, endpoint, page, query or sync is slow, wants a performance review or audit, asks "will this scale", plans a load test, wants to know which optimizations are worth it, or shares a performance checklist and asks what applies to their system, even if they never say the word "performance".
---

# bottleneck

Most performance advice is a list of things to add. Most systems only have one or two things
that actually make them slow, and the rest of the list is cost without benefit. This skill finds
the real bottleneck, proves it with a measurement, and tells the user which techniques are worth
doing **for their system at their scale**, which ones already exist, and which ones are not worth
it yet.

Answer in the user's language. Keep the technique names in English when they are industry terms.

## Ground rules

These exist because a performance audit touches production systems and people's time.

1. **Evidence or "Unknown".** Every verdict cites what you looked at: a file and line, a command
   output, a header, a number. If you could not check it, the verdict is `Unknown` with the exact
   thing needed to check it. A confident wrong verdict is worse than an honest gap.
2. **Read-only by default.** Audit without changing code, config or data. Implement only when the
   user asks, one item at a time.
3. **Never load-test production.** Single requests to read headers are fine. Load tests run only
   against a test/staging environment, and if that environment shares a server or database with
   production, say so and watch production health during the run.
4. **Scale decides the verdict.** Redis, CDNs, queues and extra instances are right for some
   systems and pure overhead for others. Ask for (or measure) the numbers that matter: active
   users, requests per second, biggest tables, payload sizes, network of the end users.
5. **Bottleneck first.** Speeding up a part that is not the bottleneck does not make the system
   faster. Measure before recommending, and rank fixes by how much of the real slow path they
   remove.

## Workflow

### 1. Scope (ask only what you cannot discover)

Find out, from the conversation or the repo, before asking:

- Which parts exist: API, database, web frontend, mobile app, background jobs.
- Where the code is (paths) and whether there is a test/staging URL.
- Whether you can run read-only database queries (and against which environment).
- What "slow" means to them: a specific screen, endpoint, sync, page load, or "in general".
- Scale: users, traffic, data size, and the end user's network (office fiber vs. rural 3G changes
  priorities a lot).

If something important is missing and cannot be discovered, ask one short question with the
options, then continue with what you have.

### 2. Recon

Run the repo scanner to detect the stack and collect signals quickly:

```bash
python3 <skill-dir>/scripts/scan_repo.py <repo-path> [<repo-path> ...]
```

It reports the stack (frameworks, ORM, database driver, bundler) and heuristic signals: missing
compression middleware, queries inside loops, `SELECT *`, HTTP calls without timeout, missing
route-level code splitting, images without lazy loading, render-blocking third-party scripts, and
more. Signals are leads, not verdicts: open the file and confirm before using one as evidence.

If there is a live URL, check transport-level behavior (compression, caching, HTTP version, TTFB,
payload size) with:

```bash
bash <skill-dir>/scripts/check_http.sh <url> [<url> ...]
```

Use a public or test endpoint. For authenticated endpoints, pass a header through the
`AUTH_HEADER` environment variable; never print tokens in the report.

### 3. Baseline measurement

Before judging, get numbers for the slow path the user cares about:

- **API**: p50/p95 of the slow endpoint at a few concurrency levels (1, 5, 10, 25, 50), using
  `scripts/k6_template.js` against test/staging. Stop raising load if errors appear or production
  health degrades. Note that rate limiters will distort results: detect 429s and report them
  instead of reading them as server speed.
- **Database**: the slow queries with `EXPLAIN (ANALYZE, BUFFERS)`, cache hit ratio and table
  sizes. Read `references/database.md` for ready read-only diagnostic queries.
- **Web**: bundle size, Core Web Vitals (Lighthouse or field data), request waterfall.
- **Mobile**: duration of the slow flow on a real device and a throttled network.

Write down the baseline. Every recommendation later is judged against it.

### 4. Audit the 31 techniques

Go area by area and read the reference file for the areas that exist in this system:

| Area | Reference | Techniques |
|---|---|---|
| Database and queries | `references/database.md` | N+1 queries, indexes, select only needed columns, connection pool, pagination, server close to the database |
| Backend and server | `references/backend.md` | Brotli/Gzip compression, cache (Redis), queue for slow work, timeouts on external calls, parallel independent requests, multiple instances behind a load balancer |
| Network and delivery | `references/network.md` | CDN for static files, browser cache for static assets, WebP/AVIF images, lazy loading off-screen images, self-hosted and limited fonts, deferring third-party scripts |
| Frontend payload | `references/frontend.md` | Code splitting per route, server or build-time rendering, removing unused dependencies, virtualized long lists, avoiding unnecessary re-renders |
| Perceived speed | `references/perceived.md` | Skeleton loading, optimistic UI, debounce on search/autocomplete, deduplicating API calls, streaming AI responses token by token |
| Measurement | `references/measure.md` | Tracing slow requests (OpenTelemetry), real user monitoring, testing on a real phone and slow network |

Skip areas that do not exist (no frontend means the frontend techniques are `N/A`, said once, not
31 times). Each reference explains, per technique, how to detect it per stack, what evidence to
collect, when it is worth doing and when it is not, and how to fix it.

### 5. Verdicts

Give each technique exactly one verdict:

- **Done**: already in place. Cite where.
- **Worth fixing**: missing, and the evidence says it costs real time at this scale. Say the
  expected gain and the effort.
- **Not worth it now**: missing, but the gain is negligible at this scale. Always state the
  threshold that would flip it ("revisit when the biggest table passes ~1M rows", "when p95 of X
  passes 1 s"). It is often the most useful verdict, because it keeps the user from work that
  would not help.
- **N/A**: does not apply to this architecture.
- **Unknown**: could not verify. State exactly what is needed.

### 6. Prioritize

Rank the "Worth fixing" items by gain on the measured slow path divided by effort. Prefer, in
order: changes that remove work entirely (skip unchanged data, avoid the call), changes that
remove round trips (batch, join, parallelize), changes that shrink bytes on the wire
(compression, fewer columns), and only then infrastructure (cache layers, more instances).

Group them into steps that can each be shipped and measured on their own. A step that needs a
schema change must be a numbered migration file, never a manual command.

### 7. Report

Use this structure. Keep it skimmable: short sentences, tables, no wall of text.

```markdown
# Performance audit: <system>

## The bottleneck
<One or two sentences: where the time goes, with the number that proves it.>

## Baseline
<Table of the measurements taken, with environment, date and method.>

## Verdicts
| # | Technique | Verdict | Evidence | Gain / effort |
|---|---|---|---|---|
<31 rows, or one row per area marked N/A when a whole area does not exist>

## Plan
1. <Step>: expected gain, effort, how it will be measured.
2. ...

## Not worth it now
<Each item with the threshold that would change the verdict.>

## Unknowns
<What could not be checked and what is needed.>
```

Save the report as `performance-audit.md` in the repo root (or where the user asks) and summarize
the bottleneck and the top 3 steps in the chat.

### 8. Implementing (only when asked)

One step at a time:

1. Write tests that pin the current behavior of the code you will touch, and run them.
2. Make the change.
3. Run the same tests.
4. Re-run the baseline measurement with the same method and compare.
5. Report the before/after numbers. If the gain is not there, say so and revert or rethink.

## Common traps

- **Reading a rate limiter as slowness.** A wall of 429s caps throughput at the limit, not at the
  server's capacity.
- **Indexing everything.** Each index costs on every write; on small tables the planner ignores
  them. Index the access paths the slow queries actually use.
- **Caching before measuring.** If the database already serves everything from memory, a cache
  layer adds a failure mode and stale data without making anything faster.
- **Measuring from far away.** Load generated from a laptop over the internet includes that
  network. Note it in the baseline, and compare like with like.
- **Trusting staging stats for production decisions.** Index usage counters on a test database
  say nothing about production traffic. Do not drop an "unused" index based on staging.
