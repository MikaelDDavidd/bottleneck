# Frontend payload

Techniques 19 to 23.

## 19. Code splitting per route

**Detect.** Size of the main bundle (`dist/assets/*.js`, `check_http.sh` on the main script with
and without compression). Route-level lazy imports: `React.lazy` + `Suspense`, TanStack Router
`autoCodeSplitting`, Next.js/Nuxt/SvelteKit (split by default), Angular `loadComponent`. The
scanner reports whether any lazy route import exists.

**Worth fixing when** the main bundle is large (hundreds of KB compressed) and most users only
open a few screens, especially on mobile networks.
**Not worth it when** the app is small, or it is an internal tool used on fast networks by a few
people: the gain exists but is low priority. Say so.

**Fix.** Lazy-load routes and heavy widgets (charts, editors, maps). Check the result with
`vite-bundle-visualizer`/`rollup-plugin-visualizer`/`webpack-bundle-analyzer`.

## 20. Server-side or build-time rendering

**Detect.** Pure client-side SPA serving an empty `<div id="root">`; public pages that need SEO or
fast first paint (landing, blog, product pages).

**Worth fixing when** public pages depend on search/social previews or show content late on slow
devices.
**Not worth it when** the app is behind a login (dashboards, admin panels): SSR adds a server and
complexity for little gain.

**Fix.** Static generation for content pages (Astro, Next/Nuxt SSG, Vite prerender plugins),
SSR only where data is per request and SEO matters.

## 21. Remove unused dependencies

**Detect.** `npx depcheck` / `knip` for unused packages, bundle visualizer for heavy ones (moment,
lodash full import, icon packs imported whole, chart libraries), duplicate versions. In backends,
unused SDKs slow cold starts and widen the attack surface. In Flutter, `dart pub deps` and
unused packages in `pubspec.yaml`.

**Worth fixing when** a heavy package is shipped to users and barely used, or packages are
clearly dead.
**Not worth it when** the bundle is already small: tidy up opportunistically.

**Fix.** Remove dead packages, import per function (`lodash-es/debounce`), swap heavy libs for
light ones (date-fns/dayjs for moment), tree-shakeable icon imports.

## 22. Virtualize long lists

**Detect.** Lists/tables rendering hundreds or thousands of rows at once (`.map` over all rows in
React, `Column` with many children in Flutter, `ScrollView` instead of `FlatList`).

**Worth fixing when** lists can exceed a few hundred items and scrolling or first render is slow.
**Not worth it when** lists are paginated or short. Flutter `ListView.builder` and React Native
`FlatList` are already virtualized.

**Fix.** TanStack Virtual, react-window, `ListView.builder`/`SliverList`, `FlatList` with
`getItemLayout`.

## 23. Avoid unnecessary re-renders

**Detect.** React Profiler "why did this render", state lifted too high, context providers with
values recreated every render, inline objects/functions passed to memoized children. Flutter:
`setState` high in the tree, missing `const` constructors, a reactive wrapper (GetX `Obx`,
`Consumer`, `BlocBuilder`) around a whole screen instead of the part that changes.

**Worth fixing when** profiling shows a measurable delay on interaction (typing, scrolling,
toggling).
**Not worth it when** nothing is measurably slow: blanket `useMemo`/`memo` adds complexity.
React Compiler can handle most of it automatically.

**Fix.** Move state down, split contexts, memoize where the profiler points, `const` widgets and
narrow reactive scopes in Flutter.
