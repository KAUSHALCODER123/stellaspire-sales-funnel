---
description: "Check the setup: DNS (SPF, DKIM, DMARC), the Gmail connector, Hiresome and Apollo keys, scripts, labels, and that sending works without approval."
---

# Setup check

> **Where this runs.** This file runs from the repository checkout, which is the current directory: scripts are `scripts/ss.py`, settings and lists are in `config/`. When a step says to run a skill or agent of this plugin, open its file in this repository (`skills/<name>/SKILL.md` or `agents/<name>.md`) and follow it. For an agent, start a subagent with that file's text as its instructions, on the model named in its header. Ignore any other installed copy of the stellaspire-outreach plugin: it may be out of date.

Run every check, do not stop at the first failure, and print a table: check, PASS or FAIL, detail. Fix only the labels. Everything else is reported for Nikita.

1. **Settings.** First read the newest `SS Settings` note (label `SS/Settings`, if any) and run `ss.py load-settings` with its JSON as `overrides` (`{}` if none); an `error` is a FAIL for the note. Then read `config/settings.json` with those overrides applied (`effective` in the output). Report `send_mode`, `paused`, `warmup_start_date` (FAIL if missing), `alert_email`, and the sending address. The sending domain is the part after `@` of the sending address.
2. **DNS** for the sending domain. Use `nslookup -type=txt <domain>` (or `dig +short txt <domain>`):
   - SPF: a TXT record starting `v=spf1` that includes `_spf.google.com`.
   - DMARC: `nslookup -type=txt _dmarc.<domain>`, a record starting `v=DMARC1`. WARN if `p=none` after the first month.
   - DKIM: `nslookup -type=txt google._domainkey.<domain>` (also try the selector Google Workspace shows in Admin). FAIL if no `v=DKIM1` record.
3. **Gmail connector** reachable, and it is the `.in` mailbox: look up the connected profile or search for one message. FAIL if it is any other mailbox, and in particular the `.com` one.
4. **Hiresome key**: `ss.py hiresome` with `{"action": "ping"}`. PASS if `ok` is true; `hiresome_token_missing` means `HIRESOME_TOKEN` isn't in the environment variables, and `hiresome_auth` means the token is wrong or expired. `network_blocked:<host>` means this session's network blocks the site, not that the key is wrong: set the environment's Network access to Full (or add `api.apollo.io` and `stellaspire.hiresome.ai` to its allowed domains), and run the check from a session that uses that environment.
5. **Apollo key**: `ss.py apollo` with `{"action": "search_orgs", "keywords": ["software"], "locations": ["India"], "headcount": [50, 500], "per_page": 1}`. PASS if it returns results. `apollo_auth` means `APOLLO_API_KEY` is missing from the environment variables or is wrong. Never print the key. If it fails with `network_blocked:api.apollo.io` or `apollo_auth`, test the Apollo connector instead with its free `apollo_usage_stats_credit_usage_stats` tool: PASS (via connector) if it answers, and report the credits it shows. The connector asks for approval before it spends credits, so it works in chat but not in scheduled runs; say that plainly, because the daily task still needs the key and Full network access. FAIL if neither works.
6. **Scripts**: 
```
python3 scripts/ss.py today <<'JSON'
{"sent_today": 0, "drafted_today": 0, "followups_due": 0}
JSON
```
PASS if it returns JSON with `send_day`. FAIL on a missing module such as `holidays`.
7. **Labels.** Make sure these exist in the `.in` mailbox, creating any that are missing and listing what you created: `SS/Step-1`, `SS/Step-2`, `SS/Step-3`, `SS/Step-4`, `SS/Step-5`, `SS/Replied`, `SS/Interested`, `SS/Not-now`, `SS/Wrong-person`, `SS/OOO`, `SS/Do-not-contact`, `SS/Bounced`, `SS/Meeting`, `SS/Won`, `SS/Stopped`, `SS/Alerted`, `SS/Lessons`, `SS/Campaigns`, `SS/Settings`. Also one `SS/C-<slug>` label for each campaign (newest `SS Campaign <slug>` note per slug, plus `config/campaigns.json`) whose status is `active`. Also check that `when_no_campaign` in settings is `wait` or `default`, and that campaigns parse (run `ss.py campaign` with `{"campaigns": [<parsed notes>], "counts": {}, "new_cap": 5}`; an `error` is a FAIL).
8. **Sending without approval.** Using the Gmail connector, send a short email from the `.in` mailbox to `alert_email`, subject `Stellaspire setup check <date>`, body "Setup check. If you read this, sending works." If it sends with no approval prompt, PASS. If it fails or waits for approval, FAIL and say clearly: "Scheduled runs will stop at this point. Fix the connector's approval setting before relying on send mode or on alerts." Do not retry in a loop.
9. **Gmail signature.** Create a throwaway draft to `alert_email` (subject `Stellaspire signature test`) with a one-line `htmlBody` and `includeSignature: true`, then read it back with `get_draft` (full content). PASS if its HTML contains `gmail_signature`. If it doesn't, WARN: "No default Gmail signature is set, or the connector cannot add it: drafts will end with just the sign-off. Set a default signature in Gmail settings." Delete the test draft.
10. **LinkedIn doc.** If `linkedin_doc_url` is set, open it through the Claude Docs connector: PASS if it's readable. If it's empty, create a doc titled "Stellaspire LinkedIn notes" with a one-line intro ("Connection notes for LinkedIn. Newest day first.") and an empty table with the columns `Date | Name | Title | Company | Profile link | Note | Status`. Then ask Nikita: "Shall I save this doc link as your LinkedIn notes doc?" Only after an explicit yes, save it as in `/stellaspire-outreach:settings`: `ss.py settings-check` with the newest `SS Settings` overrides plus `linkedin_doc_url`, then send a new note-to-self with subject `SS Settings` and the full override JSON, labelled `SS/Settings`. Without a yes, WARN, not FAIL: notes go in the report until it's set.
11. **Firecrawl** (optional). If a Firecrawl tool is available, run one `firecrawl_scrape` on `https://stellaspire.com`: PASS or FAIL. If it isn't available, WARN: "research falls back to WebSearch and WebFetch".
12. Print the table, then a one-line verdict: ready for `draft` mode, ready for `send` mode, or not ready, with the failing checks.
