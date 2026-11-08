---
type: llm
focus: trace
weight: 1
---

performance-audit.md flags SELECT * (or select('*')) pulling unused wide columns such as photo_base64 or notes.
