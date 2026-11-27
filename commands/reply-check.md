---
description: "Replies only. Classify new replies, label them, stop sequences, alert Nikita on interested ones. Used for the midday and evening runs."
---

# Reply check

> **Where this runs.** This file runs from the repository checkout, which is the current directory: scripts are `scripts/ss.py`, settings and lists are in `config/`. When a step says to run a skill or agent of this plugin, open its file in this repository (`skills/<name>/SKILL.md` or `agents/<name>.md`) and follow it. For an agent, start a subagent with that file's text as its instructions, on the model named in its header. Ignore any other installed copy of the stellaspire-outreach plugin: it may be out of date.

Handle replies only. Write no new outreach and no follow-ups.

Hard rules: if a script says no, do not do it; never edit config or settings (only read the `SS Settings` note); never create, change or activate a campaign (only read `SS Campaign` notes); on any connector failure stop and report; the plugin directory is read-only, write no files.

0. Run lock: search for a note-to-self with subject `SS Run lock` created less than 90 minutes ago. If there is one, a daily run is in progress: stop now and print "daily run in progress". Create no lock note of your own. A lock older than 90 minutes is stale: ignore it.
0b. Settings overrides, before any other script call. Search the `.in` mailbox for the newest note with subject `SS Settings` (label `SS/Settings`, body is JSON of overrides only) and run `ss.py load-settings` with `{"overrides": <that JSON>}` (use `{"overrides": {}}` when there is no note, which also clears an old override left on this machine). If the body is not valid JSON or the script exits non-zero, ignore the note, run it again with `{"overrides": {}}`, use the plugin defaults, and list the note under Needs Nikita with the problems. Only READ this note: never create, change or delete it.
1. Health first:
```
python3 scripts/ss.py health <<'JSON'
{"sent_14d": 0, "bounced_14d": 0, "complaints": 0}
JSON
```
Fill the counts from Gmail as in the daily run (last 14 days). Replies are still handled when `pause` is true, since a complaint or bounce needs labelling. Report the verdict.
1b. Missing-report alarm. Only on a run at or after 12:00 IST, and not in `dry_run`. Search the `.in` mailbox's Sent folder for today's daily report (subject `Stellaspire outreach — <YYYY-MM-DD>`, today's IST date). If it's missing, and no `Stellaspire: morning run did not report` email was sent today, email `alert_email`:
   - subject `Stellaspire: morning run did not report <YYYY-MM-DD>`
   - body: today's 07:07 run sent no report. Likely causes: the scheduled task failed or was turned off, a connector needs signing in again, or an approval prompt stopped it. Check the task's run history in Claude. Replies are still being handled.
   Add a line about it to this run's report. Send this alarm once per day only.
2. Run the `handle-replies` skill. It sends the alert for any interested reply (every `send_mode` except `dry_run`).
3. Write a short report: replies handled by class, labels applied, alert status, anything under Needs Nikita. If an alert failed, the first line is `ALERT NOT SENT`. Email it to `alert_email` only if something was handled (subject `Stellaspire replies — <YYYY-MM-DD HH:MM>`, not in `dry_run`). Print it as the final message.
