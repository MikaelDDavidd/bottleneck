# bottleneck

A Claude skill that audits the performance of a real system (API, database, web frontend, mobile
app) and tells you **which optimizations are worth doing for your system at your scale**, with
the evidence for each verdict.

Most performance checklists tell you to add everything: Redis, a CDN, a queue, more instances.
Most systems are slow because of one or two things, and the rest of the list is cost without
benefit. `bottleneck` finds the real bottleneck, proves it with a measurement, and says out loud
what you should **not** spend time on yet, with the number that would change its mind.

## What it does

1. **Recon.** Detects the stack and scans the code for leads: queries inside loops (N+1),
   `SELECT *`, missing compression, HTTP calls without timeout, SPAs without code splitting,
   images without lazy loading, render-blocking scripts. Tests and prototypes are left out so the
   leads point at production code.
2. **Transport check.** Reads the live headers of an endpoint or asset: compression, cache
   policy, HTTP version, time to first byte, and how much smaller the response would be with
   gzip.
3. **Baseline.** Measures the slow path before judging (k6 template included, staging only),
   plus read-only database diagnostics (`EXPLAIN`, cache hit ratio, unused indexes, top queries).
4. **31 techniques, one verdict each.** Database, backend, network, frontend payload, perceived
   speed and measurement. Every technique gets `Done`, `Worth fixing`, `Not worth it now`, `N/A`
   or `Unknown`, always with the file, header or number behind it.
5. **Plan.** Ranks the fixes by gain on the measured slow path divided by effort, in steps that
   can each be shipped and measured.
6. **Report.** Writes `performance-audit.md` and summarizes the bottleneck and the top steps.

It audits read-only. It changes code only when you ask, one step at a time, with tests before and
after and the same measurement repeated.

## Example

> "Customers say the orders screen takes 4 to 6 seconds to open on Monday mornings. Can you
> check what's actually worth fixing? API and web are in ./slow-shop."

That is the test case shipped in `bottleneck/evals/`, a small fictional ordering app. The audit
finds an N+1 loop that loads the items of each order one query at a time (the bottleneck), no
index on `order_items.order_id`, API responses sent without compression and with `SELECT *`, and
an outbound HTTP call without a timeout. Redis and a CDN come back as **not worth it now** for
about 40 concurrent users, each with the number that would change that verdict.

## Install

Claude Code (personal skills):

```bash
git clone https://github.com/MikaelDDavidd/bottleneck && cp -R bottleneck/bottleneck ~/.claude/skills/bottleneck
```

Then ask Claude about a slow endpoint, page or app, or type `/bottleneck`.

Claude.ai: upload the `bottleneck.skill` file from the [releases page](https://github.com/MikaelDDavidd/bottleneck/releases/latest) in Settings > Capabilities > Skills.

## What's inside

```
bottleneck/
├── SKILL.md                 workflow, verdict rules, report template
├── references/              one file per area, per technique: detect, evidence, worth it when, fix
│   ├── database.md          (with read-only PostgreSQL diagnostic queries)
│   ├── backend.md
│   ├── network.md
│   ├── frontend.md
│   ├── perceived.md
│   └── measure.md
└── scripts/
    ├── scan_repo.py         stack detection and code leads
    ├── check_http.sh        compression, cache and timing of live URLs
    └── k6_template.js       parametrized load test for before/after numbers
```

## Safety

- Never runs load tests against production.
- Read-only by default: no code, config or data changes without an explicit request.
- Never prints tokens passed for authenticated checks.
- Schema changes are proposed as numbered migration files, never as manual commands.

## Credits

The list of 31 techniques was inspired by a short video by
[@gustagoat.ai](https://www.instagram.com/gustagoat.ai/) on Instagram. The text, structure,
verdict rules, checks and scripts in this repository are original.

## License

MIT. See [LICENSE](LICENSE).
