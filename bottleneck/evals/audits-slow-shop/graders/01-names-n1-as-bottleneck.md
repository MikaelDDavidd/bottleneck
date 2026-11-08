---
type: llm
focus: trace
weight: 1
---

performance-audit.md names the loop in GET /api/orders that runs one order_items query per order (N+1) as the main cause of the slow orders screen, citing src/server.js.
