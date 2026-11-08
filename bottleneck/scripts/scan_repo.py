#!/usr/bin/env python3
"""Fast, read-only recon of one or more repositories for a performance audit.

Detects the stack and collects heuristic signals for the 31 techniques. Signals are
leads: open the file and confirm before using one as evidence.

    python3 scan_repo.py <repo-path> [<repo-path> ...] [--json] [--include-tests]

Tests, fixtures, prototypes and scripts/ folders are left out of the signal list by default
(they are counted at the end) so the leads point at production code.
"""
import json
import os
import re
import sys

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt", "out", "coverage", ".dart_tool",
    "ios", "android", "Pods", "vendor", "__pycache__", ".venv", "venv", ".turbo", ".cache",
    "target", ".gradle", "tmp", "storybook-static",
}
CODE_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".dart", ".rb", ".go",
            ".java", ".kt", ".php", ".vue", ".svelte", ".html"}
MAX_FILE_BYTES = 400_000
MAX_HITS_PER_SIGNAL = 8


def read(path):
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return ""
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            yield os.path.join(dirpath, name)


def detect_stack(root):
    stack, deps = [], set()
    pkg = os.path.join(root, "package.json")
    if os.path.exists(pkg):
        try:
            data = json.loads(read(pkg) or "{}")
            for key in ("dependencies", "devDependencies"):
                deps.update((data.get(key) or {}).keys())
        except json.JSONDecodeError:
            pass
        known = {
            "express": "Express", "fastify": "Fastify", "@nestjs/core": "NestJS", "koa": "Koa",
            "next": "Next.js", "nuxt": "Nuxt", "react": "React", "vue": "Vue", "svelte": "Svelte",
            "@angular/core": "Angular", "vite": "Vite", "webpack": "webpack", "astro": "Astro",
            "knex": "Knex", "prisma": "Prisma", "@prisma/client": "Prisma", "sequelize": "Sequelize",
            "typeorm": "TypeORM", "mongoose": "Mongoose", "drizzle-orm": "Drizzle", "pg": "node-postgres",
            "mysql2": "mysql2", "redis": "Redis client", "ioredis": "Redis client",
            "bullmq": "BullMQ", "bull": "Bull", "socket.io": "Socket.IO",
            "@tanstack/react-query": "TanStack Query", "swr": "SWR", "compression": "compression middleware",
            "@opentelemetry/api": "OpenTelemetry", "@sentry/node": "Sentry", "web-vitals": "web-vitals",
            "react-native": "React Native", "@tanstack/react-router": "TanStack Router",
        }
        stack += [label for dep, label in known.items() if dep in deps]
    for marker, label in [
        ("pubspec.yaml", "Flutter/Dart"), ("requirements.txt", "Python"), ("pyproject.toml", "Python"),
        ("manage.py", "Django"), ("Gemfile", "Ruby"), ("go.mod", "Go"), ("pom.xml", "Java/Maven"),
        ("build.gradle", "Gradle"), ("composer.json", "PHP"), ("docker-compose.yml", "Docker Compose"),
        ("Dockerfile", "Docker"), ("nginx.conf", "nginx"),
    ]:
        if os.path.exists(os.path.join(root, marker)):
            stack.append(label)
    pubspec = read(os.path.join(root, "pubspec.yaml"))
    for dep, label in [("get:", "GetX"), ("sqflite", "SQLite (sqflite)"), ("dio:", "Dio"),
                       ("flutter_bloc", "Bloc"), ("riverpod", "Riverpod")]:
        if dep in pubspec:
            stack.append(label)
    return sorted(set(stack)), deps


# Paths that are not production code: tests, fixtures, prototypes and scratch HTML. Signals
# found there are counted separately instead of mixed with real leads.
NON_PROD_DIR = re.compile(
    r"(^|/)(tests?|__tests__|spec|specs|e2e|cypress|playwright|fixtures?|mocks?|__mocks__|examples?|"
    r"samples?|demo|prototypes?|proto|drafts?|scratch|playground|stories|storybook|ai_ui_made|scripts)(/|$)",
    re.I,
)
NON_PROD_FILE = re.compile(r"\.(test|spec|stories|e2e)\.[a-z]+$|_test\.(py|go|dart)$|^test_.*\.py$", re.I)


def is_non_prod(rel):
    return bool(NON_PROD_DIR.search(os.path.dirname(rel)) or NON_PROD_FILE.search(os.path.basename(rel)))


# A call that reaches the database. Covers query builders, ORMs and raw drivers.
QUERY_CALL = re.compile(
    r"await\s+(?:this\.|self\.)?(?:\w+\.)*?(?:db|knex|trx|prisma|query|pool|client|sequelize|"
    r"repo|repository|model|em|manager|supabase|\w+Model|\w+Repository)\s*[.(\[]"
    r"|\.objects\.(?:get|filter|all|create)\(|session\.query\(|cursor\.execute\(|\.find(?:One|Many|All|ById)?\(\s*\{?"
)
LOOP_START = re.compile(
    r"^\s*(?:for\s*\(|for\s+(?:await\s+)?\(?\s*(?:const|let|var)?\s*[\w\[\]{}, ]+\s+(?:of|in)\b|"
    r"for\s+\w+(?:\s*,\s*\w+)*\s+in\s+.+:\s*$|while\s*\(|while\s+.+:\s*$)"
    r"|\.forEach\(|\.each\s+do\b|\.each\s*\{"
)
FUNC_DEF = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function\s+(\w+)|(\w+)\s*\([^)]*\)\s*\{|(?:const|let)\s+(\w+)\s*=\s*async)"
    r"|^\s*(?:async\s+)?def\s+(\w+)\s*\("
)
KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "function", "constructor"}
BODY_LIMIT = 60


def indent_of(line):
    return len(line) - len(line.lstrip(" \t"))


def body_lines(lines, i):
    """Lines of the block that starts at line i, bounded by indentation (works for braces and Python)."""
    base = indent_of(lines[i])
    out = []
    for j in range(i + 1, min(len(lines), i + 1 + BODY_LIMIT)):
        line = lines[j]
        if not line.strip():
            continue
        if indent_of(line) <= base and not line.strip().startswith((".", ")", "}).", "?", ":")):
            break
        out.append((j, line))
    return out


def query_functions(lines):
    """Names of functions/methods in this file whose body calls the database directly."""
    names = set()
    for i, line in enumerate(lines):
        m = FUNC_DEF.match(line)
        if not m:
            continue
        name = next((g for g in m.groups() if g), None)
        if not name or name in KEYWORDS:
            continue
        if any(QUERY_CALL.search(l) for _, l in body_lines(lines, i)):
            names.add(name)
    return names


def loops_with_queries(lines, helpers):
    """Yield (loop line, query line, how) for loops whose body awaits a query or a query helper."""
    helper_call = re.compile(r"await\s+(?:this\.|self\.)?(" + "|".join(map(re.escape, helpers)) + r")\s*\(") if helpers else None
    for i, line in enumerate(lines):
        if not LOOP_START.search(line):
            continue
        for j, inner in body_lines(lines, i):
            if QUERY_CALL.search(inner):
                yield i + 1, j + 1, "direct query"
                break
            if helper_call and helper_call.search(inner):
                yield i + 1, j + 1, f"calls {helper_call.search(inner).group(1)}(), which queries the database"
                break


# Each signal: (technique number, name, regex, file filter, explanation)
SIGNALS = [
    (3, "SELECT * / unscoped select", re.compile(r"select\s+\*\s+from|\.select\(\s*['\"]\*['\"]\s*\)", re.I),
     None, "Fetches every column; check for wide columns not used by the caller. Query builders without .select() also fetch everything."),
    (10, "axios call without explicit timeout", re.compile(r"axios(\.(get|post|put|patch|delete|request))?\((?:(?!timeout)[^;])*\)\s*;", re.S),
     (".js", ".ts", ".mjs", ".cjs"), "No timeout means a slow provider can hold the request indefinitely. A global axios.create({timeout}) also counts."),
    (10, "fetch without AbortSignal/timeout", re.compile(r"await\s+fetch\((?:(?!signal)[^;])*\)\s*;", re.S),
     (".js", ".ts", ".tsx", ".mjs"), "fetch has no default timeout."),
    (10, "Python requests without timeout", re.compile(r"requests\.(get|post|put|delete|patch)\((?:(?!timeout)[^)])*\)"),
     (".py",), "requests waits forever without timeout=."),
    (16, "<img> without loading=\"lazy\"", re.compile(r"<img(?![^>]*loading=)[^>]*>", re.I),
     (".html", ".jsx", ".tsx", ".vue", ".svelte"), "Off-screen images load eagerly. Keep the above-the-fold (LCP) image eager."),
    (17, "Google Fonts link", re.compile(r"fonts\.googleapis\.com"), None,
     "Third-party font host on the critical path; consider self-hosting and fewer weights."),
    (18, "Script without async/defer", re.compile(r"<script(?![^>]*\b(async|defer|type=\"module\"))[^>]*src=", re.I),
     (".html",), "Render-blocking script."),
    (19, "Route-level lazy import (code splitting present)", re.compile(r"React\.lazy\(|lazy\(\s*\(\)\s*=>\s*import\(|loadComponent|autoCodeSplitting"),
     None, "Presence means code splitting exists somewhere; absence in a large SPA is a lead."),
    (26, "Debounce present", re.compile(r"debounce|useDeferredValue|debounceTime", re.I), None,
     "Presence suggests inputs are debounced somewhere; confirm on the slow search."),
]

COMPRESSION_HINTS = re.compile(
    r"require\(['\"]compression['\"]\)|from ['\"]compression['\"]|GZipMiddleware|gzip\s+on;|compress:\s*true|encode\s+gzip|\bbrotli\b",
    re.I,
)
TIMEOUT_DEFAULT = re.compile(r"axios\.create\(\{[^}]*timeout", re.S)
POOL_HINT = re.compile(r"pool\s*:\s*\{[^}]*max\s*:\s*(\d+)|connection_limit=(\d+)", re.S)
INDEX_HINT = re.compile(r"create\s+(unique\s+)?index", re.I)
N1_EXT = {".js", ".ts", ".mjs", ".cjs", ".py", ".rb", ".dart"}


def add_hit(hits, key, loc):
    bucket = hits.setdefault(key, [])
    if loc in bucket:
        return True
    if len(bucket) < MAX_HITS_PER_SIGNAL:
        bucket.append(loc)
    return len(bucket) < MAX_HITS_PER_SIGNAL


def scan(root, include_non_prod=False):
    stack, deps = detect_stack(root)
    hits, skipped = {}, {}
    files = 0
    compression, timeout_default, pools = [], [], []
    index_files = 0
    for path in walk(root):
        ext = os.path.splitext(path)[1].lower()
        rel = os.path.relpath(path, root)
        if ext == ".sql":
            if INDEX_HINT.search(read(path)):
                index_files += 1
            continue
        if ext not in CODE_EXT and not path.endswith(("nginx.conf", ".yml", ".yaml", "Caddyfile")):
            continue
        text = read(path)
        if not text:
            continue
        files += 1
        non_prod = is_non_prod(rel)
        if COMPRESSION_HINTS.search(text) and not non_prod:
            compression.append(rel)
        if TIMEOUT_DEFAULT.search(text) and not non_prod:
            timeout_default.append(rel)
        for m in POOL_HINT.finditer(text):
            pools.append(f"{rel}: max {next(g for g in m.groups() if g)}")
        if ext not in CODE_EXT:
            continue
        target = hits
        if non_prod and not include_non_prod:
            target = skipped
        lines = text.split("\n")
        if ext in N1_EXT:
            key = (1, "Query inside a loop (possible N+1)",
                   "The loop body awaits a query (or a helper that queries) once per item. Count queries per request to confirm.")
            for loop_line, query_line, how in loops_with_queries(lines, query_functions(lines)):
                if not add_hit(target, key, f"{rel}:{loop_line} (query at line {query_line}, {how})"):
                    break
        for num, name, rx, exts, why in SIGNALS:
            if exts and ext not in exts:
                continue
            for m in rx.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                if not add_hit(target, (num, name, why), f"{rel}:{line}"):
                    break
    spa = any(x in stack for x in ("React", "Vue", "Svelte", "Angular"))
    if spa and not any(k[0] == 19 for k in hits) and "Next.js" not in stack and "Nuxt" not in stack:
        hits[(19, "No route-level lazy import found",
              "SPA without code splitting ships every screen in the first download. Check the main bundle size before judging.")] = ["(whole repo)"]
    as_list = lambda d: [{"technique": n, "signal": s, "why": w, "locations": l} for (n, s, w), l in sorted(d.items())]
    return {
        "root": root,
        "files_scanned": files,
        "stack": stack,
        "compression_config_found_in": compression[:MAX_HITS_PER_SIGNAL],
        "global_http_timeout_found_in": timeout_default[:MAX_HITS_PER_SIGNAL],
        "pool_settings": pools[:MAX_HITS_PER_SIGNAL],
        "sql_files_creating_indexes": index_files,
        "signals": as_list(hits),
        "signals_in_tests_and_prototypes": {f"#{n} {s}": len(l) for (n, s, _), l in sorted(skipped.items())},
    }


def print_report(r):
    print(f"# Recon: {r['root']}")
    print(f"files scanned: {r['files_scanned']}")
    print(f"stack: {', '.join(r['stack']) or 'unknown'}")
    print(f"compression config: {', '.join(r['compression_config_found_in']) or 'NOT FOUND in code (check proxy and live headers)'}")
    print(f"global HTTP client timeout: {', '.join(r['global_http_timeout_found_in']) or 'not found'}")
    print(f"pool settings: {', '.join(r['pool_settings']) or 'not found'}")
    print(f"SQL files creating indexes: {r['sql_files_creating_indexes']}")
    print("\n## Signals (leads, confirm before using as evidence)")
    if not r["signals"]:
        print("none")
    for s in r["signals"]:
        print(f"- [#{s['technique']}] {s['signal']} — {s['why']}")
        for loc in s["locations"]:
            print(f"    {loc}")
    if r["signals_in_tests_and_prototypes"]:
        counts = ", ".join(f"{k}: {v}" for k, v in r["signals_in_tests_and_prototypes"].items())
        print(f"\n(ignored in tests/fixtures/prototypes, use --include-tests to list: {counts})")
    print()


def main(argv):
    as_json = "--json" in argv
    include = "--include-tests" in argv
    roots = [a for a in argv if not a.startswith("--")]
    if not roots:
        print(__doc__)
        return 1
    results = [scan(os.path.abspath(r), include_non_prod=include) for r in roots]
    if as_json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            print_report(r)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
