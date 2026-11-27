---
description: "Weekly funnel counts by role and by city from the SS labels, including meetings and wins. Emails it to Nikita."
---

# Weekly report

> **Where this runs.** This file runs from the repository checkout, which is the current directory: scripts are `scripts/ss.py`, settings and lists are in `config/`. When a step says to run a skill or agent of this plugin, open its file in this repository (`skills/<name>/SKILL.md` or `agents/<name>.md`) and follow it. For an agent, start a subagent with that file's text as its instructions, on the model named in its header. Ignore any other installed copy of the stellaspire-outreach plugin: it may be out of date.

Read-only on Gmail except for sending the report. Write no files.

1. From Gmail threads in the `.in` mailbox, count over the last 7 days and all-time:
   - contacted (`SS/Step-1`), reached step 2 to 5, replied (`SS/Replied`), `SS/Interested`, `SS/Not-now`, `SS/Wrong-person`, `SS/Do-not-contact`, `SS/Bounced`, `SS/Meeting`, `SS/Won`.
2. Break the counts down by role family and by city. Read role and city from each thread's first email (the opener names the role; the city when given). Group roles by family using `ss.py role-check` (its `family` field) when unsure.
   Also give a per-campaign funnel from the `SS/C-<slug>` labels (every campaign active, or finished in the last 4 weeks): contacted, reached step 2 to 5, replied, interested, meeting, won, bounced, and progress against `target_contacts`. Threads without a campaign label are listed as "no campaign".
3. Compute reply rate (replies / contacted), interested rate, bounce rate.
4. **Lessons.** Analyse the last 4 weeks of `SS/` threads. Compare reply rate and interested rate by: role family, city, subject style (for example naming the role's age, a pain line, a question), opener type (role age hook vs fresh role, from whether `role_open_days` shaped the opener), and closing-question style. Also read which follow-up step (2 to 5) got the replies. A group with fewer than 10 sends is "too early to tell": list it as such and draw no lesson from it.
   Write at most 5 short lessons, each backed by its numbers, for example "Subjects naming the role's age: 4/31 replies vs 1/40 for others". Lessons are about style and targeting only. They never touch caps, scripts, the `check-email` copy rules or safety rules.
   Store them as ONE note-to-self email from the `.in` mailbox to itself, subject `SS Lessons <YYYY-MM-DD>`, labelled `SS/Lessons` (create the label if missing). The newest note is the current one; do not edit or delete older notes. In `dry_run`, show the note in the report only. If there is nothing evidence-backed yet, write a note saying "Too early to tell" instead of inventing lessons.
5. **Suggested changes.** List anything that would need a code or settings change, for example "add Pune to target_cities" or "drop email 5 for sales roles". You never apply these; a person does, through a change to the plugin repo.
6. Write a short plain-text report: totals, the two breakdown tables, the per-campaign funnel, what worked, what did not, the lessons, and a "Suggested changes" section. No emoji.
7. Email it to `alert_email` from the `.in` mailbox, subject `Stellaspire weekly funnel — <YYYY-MM-DD>`, unless `send_mode` is `dry_run`. If the send fails, do not retry in a loop. Print the report as the final message.
