# Perceived speed

Techniques 24 to 28. These do not make the server faster; they make waiting feel shorter or
remove waiting the user would otherwise see.

## 24. Skeleton loading

**Detect.** Screens that show a blank area or a full-page spinner while loading; layout jumping
when data arrives (CLS).

**Worth fixing when** main screens wait on the network for more than a few hundred ms.
**Not worth it when** data loads from local storage instantly (offline-first apps) or the wait is
negligible.

**Fix.** Placeholders with the shape of the final content, reserved sizes to avoid layout shift,
and a real error state (not an eternal skeleton).

## 25. Optimistic UI (update without waiting for the server)

**Detect.** Save buttons that block until the server answers for actions that almost always
succeed (like, toggle, reorder, add item).

**Worth fixing when** the action is frequent and failure is rare and recoverable.
**Not worth it when** the action is irreversible or likely to fail (payments, unique
constraints) — there, show progress instead. Offline-first apps that write locally and sync later
already do the strongest form of this.

**Fix.** React Query/TanStack Query `onMutate` with rollback in `onError`, SWR `mutate` with
`optimisticData`, local-first storage with background sync on mobile.

## 26. Debounce on search and autocomplete

**Detect.** Search inputs firing a request or a heavy filter on every keystroke (network tab:
one request per letter). Check for `debounce` utilities, `useDeferredValue`, RxJS `debounceTime`,
Dart `Timer`-based debouncers.

**Worth fixing when** each keystroke hits the API or a slow filter.
**Not worth it when** already debounced (cite where), or the filter is local and instant.

**Fix.** 250 to 400 ms debounce, minimum query length, cancel the previous request
(`AbortController`) so an older response cannot overwrite a newer one. Throttle (not debounce)
for continuous events like scroll and resize.

## 27. Avoid duplicate API calls

**Detect.** The same endpoint called several times on one screen load (network tab), components
fetching the same data independently, effects running twice, refetch on every focus.

**Worth fixing when** duplicate calls hit slow endpoints or multiply load at peak.
**Not worth it when** a data layer already deduplicates (TanStack Query, SWR, Apollo with the
same key) — cite it.

**Fix.** A shared query cache keyed by request, `staleTime` tuned per data type, request
coalescing on the server for hot keys.

## 28. Stream AI responses token by token

**Detect.** Endpoints that call an LLM and return the full answer at the end; UI showing a
spinner for seconds before the text appears.

**Worth fixing when** users read AI output interactively (chat, assistants, explanations).
**Not worth it when** the output feeds another process (classification, extraction) or there is
no AI feature (`N/A`).

**Fix.** Server-Sent Events or streamed HTTP responses from the provider SDK's streaming API,
rendering tokens as they arrive, with cancel support. Watch proxies that buffer responses (nginx
`proxy_buffering off` for that route).
