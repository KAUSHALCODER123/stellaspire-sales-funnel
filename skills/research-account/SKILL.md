---
name: research-account
description: "Research each verified lead with the qualifier agent in parallel, score fit and priority with the scripts, and rank. Use during the daily run after find-leads."
allowed-tools: Agent, Bash, Read
---

# Research accounts

Input: the verified leads from `find-leads`. Output: leads ranked P0 > P1 > P2, with DQ dropped.

## 1. Run the qualifier in parallel
Never launch the `qualifier` for more leads than `research_budget` (passed by the run; 0 means none), counting companies already researched earlier in the run. Launch one `qualifier` agent per lead in a single message (batch of up to 6 at a time). Give each `today`, `name`, `domain`, `family`, the verified `roles`, the reported `lead` signal if any, and the family profile. Each returns `{"brief": {...}, "pages_opened": [...]}`.

Reject a brief that has no `pages_opened`, or whose `signals` lack a date or `source_url`. Re-apply the signal rule yourself: a signal stays only if its date is within the last 120 days and its source page names the company next to the event. Remove the rest before scoring. A brief with an empty `what_they_do` is unusable; drop the lead.

## 2. Score with the script
```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ss.py" fit <<'JSON'
{"brief": { ...brief exactly as the qualifier returned it, after removing failed signals... },
 "family": "tech_ai_data", "roles": 3, "signals": 2}
JSON
```
`roles` is the number of verified fresh roles, `signals` the number of confirmed signals. The output has `fit` and `priority` (`P0`, `P1`, `P2` or `DQ`).

## 3. Rank and cut
- Drop `DQ`. Disqualifier, country and staffing rules live in the script; do not override.
- Order P0, then P1, then P2. Within a priority, more fresh roles first, then more confirmed signals.
- Only P0 and P1 go on to contacts by default. Take P2 only when you are short of leads and the caps are not yet filled; say so in the report.
- Log every dropped lead with its reason for the report ("Skipped with reasons").

Pass the ranked list to the contacts step in `daily-run`, and report how many companies you researched of `research_budget`.
