# Database and queries

Techniques 1 to 6. Read the diagnostic queries at the end before judging anything about indexes
or memory: they turn guesses into evidence.

## 1. N+1 queries

**What it is.** Code fetches a list, then runs one more query per item (or per table, per
relation). 100 rows means 101 round trips. Each round trip is cheap alone; under concurrency they
queue for connections and CPU.

**Detect.**
- Loops with an awaited query inside: `for (...) { await db(...)/knex(...)/prisma.x.find... }`,
  `.map(async ...)` with queries, Django templates touching `obj.relation.field` in a loop,
  `forEach` over ORM results that lazy-loads relations (Sequelize, TypeORM, ActiveRecord, Hibernate).
- Logs: the same query shape repeated many times per request. Count queries per request
  (Django Debug Toolbar, `knex.on('query')`, Prisma `log: ['query']`, Bullet for Rails).
- `pg_stat_statements`: a very fast query with a huge `calls` count.

**Evidence.** The loop (file:line) and the query count for one request.

**Worth fixing when** one request makes more than ~10 queries that could be one or two, or when
the endpoint is hit concurrently (sync, list screens, dashboards).
**Not worth it when** the loop runs over a small fixed set once per day (admin job, cron).

**Fix.** Eager loading (`include`, `select_related`/`prefetch_related`, `joinedload`), one query
with `IN (...)`, a join, or `UNION ALL` of per-table queries in a single round trip. For "did
anything change?" checks, keep a per-tenant change marker and skip the whole loop when nothing
changed.

## 2. Indexes for the common queries

**Detect.** `EXPLAIN (ANALYZE, BUFFERS)` of the slow queries: `Seq Scan` on a large table followed
by `Sort` under a `LIMIT` is the classic missing composite index. Compare `seq_scan` vs `idx_scan`
in `pg_stat_user_tables` (diagnostics below). Check the migrations for which indexes exist.

**Evidence.** The plan before and after, with execution time.

**Worth fixing when** the table is large (tens of thousands of rows and up) or growing, and the
query filters by an equality column and a range/order column (tenant + updated_at). Column order:
equality first, range/order second.
**Not worth it when** the table has a few hundred rows: the planner will read the whole table
anyway, and the index only adds write cost. Say at what size to revisit.

**Fix.** A numbered migration with `CREATE INDEX CONCURRENTLY IF NOT EXISTS` (PostgreSQL; cannot
run inside a transaction; a failed build leaves an invalid index to drop and retry). Use partial
indexes (`WHERE deleted_at IS NULL`) when queries always carry that predicate. Never drop an
"unused" index based on stats from a staging database that does not get production traffic.

## 3. Select only the columns you need

**Detect.** `SELECT *`, `db(table)` without `.select(...)`, ORM `findAll` without `attributes`,
then fields removed or ignored in code; large text/JSON/blob columns travelling to list screens.

**Worth fixing when** rows carry wide columns (JSON, text, images as base64) not used by the
caller, or the payload is large for mobile users.
**Not worth it when** tables are narrow and the caller uses most columns.

**Fix.** Explicit column lists; separate "list" and "detail" queries; covering indexes for hot
queries.

## 4. Connection pool

**Detect.** Pool settings (`knexfile`, `DATABASE_URL?connection_limit`, `pg.Pool({max})`,
`CONN_MAX_AGE`, HikariCP `maximumPoolSize`), number of app processes, and the database
`max_connections`. Look for "too many connections" or long pool acquire times under load.

**Worth fixing when** there is no pool (new connection per request), or processes × pool max
exceeds `max_connections`, or many processes/serverless functions open connections (then use
PgBouncer in transaction mode).
**Not worth it when** a single app process already uses a modest pool.

**Fix.** Size by cores, not by users: a common starting point is active connections ≈ CPU cores ×
2 + disks (HikariCP "About Pool Sizing"). A bigger pool on a small server adds context switching
and memory, and makes latency worse.

## 5. Paginate API results

**Detect.** Endpoints returning whole tables, `LIMIT/OFFSET` with large offsets, clients
downloading everything at startup.

**Worth fixing when** a list can grow without bound, or offset pages get slower as the user
scrolls.
**Not worth it when** the list is small and bounded by design.

**Fix.** Keyset (cursor) pagination: `WHERE (updated_at, id) > ($1, $2) ORDER BY updated_at, id
LIMIT n`, with a matching index. For incremental sync, the cursor must never advance past rows
that may still commit with an older timestamp (advance to the last row delivered, not to "now").

## 6. Server close to the database

**Detect.** Where the app and the database run (same host, same region, different provider).
Measure a trivial query's round trip from the app host (`SELECT 1` timing).

**Worth fixing when** app and database are in different regions or providers and a request makes
several sequential queries: each round trip pays the distance.
**Not worth it when** they are already on the same host or in the same region/zone.

## Read-only diagnostic queries (PostgreSQL)

Run against the environment you are allowed to read. None of these change anything.

```sql
-- Settings that matter for a small server
SELECT name, setting, unit FROM pg_settings
WHERE name IN ('shared_buffers','effective_cache_size','work_mem','random_page_cost',
  'effective_io_concurrency','max_connections','shared_preload_libraries',
  'log_min_duration_statement','autovacuum_vacuum_scale_factor');

-- Is the working set in memory? (close to 99% means memory is not the bottleneck)
SELECT datname, round(100.0*blks_hit/nullif(blks_hit+blks_read,0),2) AS hit_pct
FROM pg_stat_database WHERE datname = current_database();

-- Biggest tables, dead rows, sequential vs index scans
SELECT relname, n_live_tup, n_dead_tup, seq_scan, seq_tup_read, idx_scan,
       pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 20;

-- Indexes never used since stats reset (unique ones enforce rules: keep them)
SELECT s.relname, s.indexrelname, s.idx_scan, pg_size_pretty(pg_relation_size(s.indexrelid))
FROM pg_stat_user_indexes s JOIN pg_index i ON i.indexrelid = s.indexrelid
WHERE s.idx_scan = 0 AND NOT i.indisunique ORDER BY pg_relation_size(s.indexrelid) DESC;

-- Top queries by total time (needs pg_stat_statements in shared_preload_libraries)
SELECT calls, round(total_exec_time) AS total_ms, round(mean_exec_time,2) AS mean_ms,
       left(query, 120) AS query
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 15;
```

Interpretation notes:
- Default `shared_buffers` (128MB) on a multi-GB server is a sign nobody tuned the database, but
  if the hit ratio is already ~99.9% the tuning will not change much today.
- No `pg_stat_statements` and `log_min_duration_statement = -1` means nobody can see slow queries:
  recommending visibility first is usually right.
- Changing `shared_buffers` or `shared_preload_libraries` needs a restart: flag it, and never do
  it on a shared production server without the owner.

For MySQL use `performance_schema.events_statements_summary_by_digest` and `EXPLAIN ANALYZE`; for
MongoDB, `explain("executionStats")` and the profiler.
