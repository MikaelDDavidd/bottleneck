# slow-shop

Small B2B ordering app for farm supply stores.

- ~300 active customers, peaks of ~40 concurrent users on Monday mornings.
- PostgreSQL 15 on the same VM as the API (4 vCPU, 8 GB). Biggest table: `order_items`, ~180k rows.
- Customers use the web app on desktop and mobile; many are in rural areas on 3G/4G.
- Complaint: "the orders screen takes 4 to 6 seconds to open on Monday mornings".
- Staging: https://staging.slow-shop.example (not reachable from this sandbox).
