#!/usr/bin/env bash
# Transport-level checks for one or more URLs: compression, caching, HTTP version, timing, size.
# Read-only: one GET per URL with compression and one without. Never use it as a load test.
#
#   bash check_http.sh https://api.example.com/health https://app.example.com/assets/index-abc.js
#
# Optional: AUTH_HEADER='Authorization: Bearer ...' to check authenticated endpoints.
# The header value is never printed.
set -u

if [ $# -eq 0 ]; then
  echo "usage: check_http.sh <url> [<url> ...]" >&2
  exit 1
fi

auth=()
if [ -n "${AUTH_HEADER:-}" ]; then
  auth=(-H "$AUTH_HEADER")
fi

for url in "$@"; do
  echo "== $url"
  headers=$(curl -s -o /dev/null -D - --compressed -H 'Accept-Encoding: br, gzip' "${auth[@]}" "$url")
  status=$(printf '%s\n' "$headers" | head -1 | tr -d '\r')
  echo "status:            $status"
  for h in content-encoding content-type cache-control etag last-modified vary server via x-cache cf-cache-status age; do
    # Some servers send a header twice (e.g. two cache-control lines): show all values joined.
    v=$(printf '%s\n' "$headers" | grep -i "^$h:" | cut -d' ' -f2- | tr -d '\r' | paste -sd ';' - | sed 's/;/; /g')
    [ -n "$v" ] && printf '%-18s %s\n' "$h:" "$v"
  done
  if ! printf '%s\n' "$headers" | grep -qi '^content-encoding:'; then
    echo "content-encoding:  (none) -> response is NOT compressed"
  fi

  # Bytes on the wire with and without compression, plus timing.
  on_wire=$(curl -s -o /dev/null -w '%{size_download} %{http_version} %{time_starttransfer} %{time_total}' \
    -H 'Accept-Encoding: br, gzip' "${auth[@]}" "$url")
  raw=$(curl -s -o /dev/null -w '%{size_download}' -H 'Accept-Encoding: identity' "${auth[@]}" "$url")
  read -r wire_bytes http_version ttfb total <<<"$on_wire"
  echo "http version:      $http_version"
  echo "bytes (as sent):   $wire_bytes"
  echo "bytes (identity):  $raw"
  if [ "$raw" -gt 0 ] 2>/dev/null && ! printf '%s\n' "$headers" | grep -qi '^content-encoding:'; then
    # What gzip would achieve, to show the gain when the server does not compress.
    gz=$(curl -s -H 'Accept-Encoding: identity' "${auth[@]}" "$url" | gzip -6 | wc -c | tr -d ' ')
    echo "bytes (if gzip -6): $gz ($(( 100 - gz * 100 / raw ))% smaller than identity)"
  fi
  echo "ttfb / total (s):  $ttfb / $total"
  echo
done
