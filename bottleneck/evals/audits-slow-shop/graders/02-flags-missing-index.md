---
type: llm
focus: trace
weight: 1
---

performance-audit.md flags that order_items has no index on order_id (and orders none on customer_id) and treats it as worth fixing given ~180k rows in order_items.
