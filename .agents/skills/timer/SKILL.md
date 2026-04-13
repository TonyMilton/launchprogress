---
name: timer
description: Start a Launchpad countdown timer. Trigger when the user asks to set a timer, start a countdown, or specifies a duration.
---

Parse the user's requested duration and convert to decimal minutes. Examples: 25m = 25, 90s = 1.5, 1h = 60, 10s = 0.1667.

Run:
```
curl -s -X POST localhost:8000/timer -H 'Content-Type: application/json' -d '{"minutes": <value>}'
```

Show the response.
