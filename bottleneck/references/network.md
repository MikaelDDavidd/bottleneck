# Network and delivery

Techniques 13 to 18. Mostly about web frontends and landing pages; for mobile apps, the image
items also apply to images downloaded at runtime.

## 13. CDN for static files

**Detect.** Where static assets are served from (`check_http.sh` shows `server`, `via`, `cf-*`,
`x-cache` headers). Where users are relative to the origin.

**Worth fixing when** users are spread far from the origin, traffic is high, or the origin is a
small server that also runs the API and database.
**Not worth it when** traffic is low and users are close to the origin; long browser caching of
hashed assets (technique 14) already removes most repeat downloads.

**Fix.** Put the static host behind a CDN (Cloudflare, CloudFront, Bunny, Fastly), keep hashed
filenames, purge only `index.html` on deploy.

## 14. Browser cache for static assets

**Detect.** `check_http.sh` on a hashed asset (`/assets/index-abc123.js`) and on `index.html`.
Correct setup: hashed assets with `cache-control: public, max-age=31536000, immutable`, HTML with
`no-cache` (revalidate) so new deploys show up.

**Worth fixing when** hashed assets come with short or no caching, or HTML is cached for a long
time (users stuck on old versions).
**Not worth it when** the headers above are already right. Cite them.

## 15. WebP or AVIF images

**Detect.** Image formats in the repo/build output and in storage (user uploads), image weights
on the heaviest pages, `<picture>`/`srcset` usage, mobile uploads of full-resolution photos.

**Worth fixing when** pages or lists show photos as JPEG/PNG weighing hundreds of KB, or users
upload camera photos that are served back at full size.
**Not worth it when** images are few and small, or are icons (use SVG).

**Fix.** Convert at build or upload time (sharp, imgproxy, a CDN image service), serve multiple
sizes with `srcset`, resize on the device before upload in mobile apps. AVIF compresses more but
encodes slower; WebP has the widest support.

## 16. Lazy loading off-screen images

**Detect.** `<img>` without `loading="lazy"` below the fold; carousels and long lists loading all
images at once. In Flutter/React Native, lists built with builders (`ListView.builder`,
`FlatList`) already create items on demand.

**Worth fixing when** pages have many images below the first screen.
**Not worth it when** the image is the main content above the fold (the LCP image should load
eagerly, ideally with `fetchpriority="high"`).

## 17. Self-hosted fonts and fewer weights

**Detect.** Google Fonts links, number of families and weights, `font-display`, preload of the
main font.

**Worth fixing when** several families/weights block text rendering, or a third-party font host
adds a connection on the critical path.
**Not worth it when** one system font stack or one self-hosted font with `font-display: swap` is
already in use.

**Fix.** Self-host (`@fontsource/*` or files), subset, keep 2 to 3 weights, `font-display: swap`,
preload the one used above the fold.

## 18. Load third-party scripts after the page

**Detect.** Analytics, chat widgets, pixels and tag managers in `<head>` without `async`/`defer`;
Lighthouse "reduce the impact of third-party code".

**Worth fixing when** third-party scripts block rendering or delay interaction on public pages
(landing, marketing, checkout).
**Not worth it when** the app is an internal tool with no third-party scripts.

**Fix.** `defer`/`async`, load after `load` or on interaction, a facade for heavy embeds (video,
chat), or move tracking server-side.
