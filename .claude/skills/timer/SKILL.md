---
name: timer
description: Control the Launchpad timer. Start, check, or cancel a timer.
argument-hint: "[duration | status | cancel]"
allowed-tools: Bash(curl:*)
---

Control the Launchpad timer at localhost:8000.

Parse $ARGUMENTS and run the appropriate curl command:

- A duration like `25m`, `5m`, `1h`, `30s`, `90` → convert to minutes (decimal) and POST:
  `curl -s -X POST localhost:8000/timer -H 'Content-Type: application/json' -d '{"minutes": <value>}'`
- `status` or no arguments → GET: `curl -s localhost:8000/timer`
- `cancel` or `stop` → DELETE: `curl -s -X DELETE localhost:8000/timer`

Show the JSON response to the user.
