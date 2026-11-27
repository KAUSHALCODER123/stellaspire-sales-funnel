---
description: "Show where the funnel stands: caps today, pause state, warm-up week, open sequences, replies waiting, drafts waiting."
---

# Status

Read-only. Write nothing, send nothing.

1. Count from Gmail: `sent_today`, `drafted_today`, open `SS/Step-*` threads by step, replies waiting (threads with an inbound message and no `SS/Replied`), unsent drafts labelled `SS/Step-*`.
2. Caps and calendar:
```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ss.py" today <<'JSON'
{"sent_today": 0, "drafted_today": 0, "followups_due": 0}
JSON
```
3. Health, with the 14-day counts from Gmail:
```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ss.py" health <<'JSON'
{"sent_14d": 0, "bounced_14d": 0, "complaints": 0}
JSON
```
4. Campaign progress: read the newest `SS Campaign <slug>` note per slug (label `SS/Campaigns`, body is JSON; skip invalid ones and say so), pass them as `campaigns`, count each campaign's threads from `SS/C-<slug>` labels and run `ss.py campaign` (input as in the daily run, including `campaigns`, `new_cap` from step 2). Show each active campaign as contacted/target, replies, interested and today's quota; list completed campaigns and whether their sequences are finished; when `waiting_for_campaign` is true say "No active campaign: new outreach is paused until Nikita starts one".
5. Print a short summary: send day or not (and why), warm-up week, caps, send mode, paused or not, health verdict, counts per step, drafts waiting to be sent, replies waiting.
