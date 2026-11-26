---
description: "Check the setup: DNS (SPF, DKIM, DMARC), Gmail and Hiresome connectors, Apollo key, scripts, labels, and that sending works without approval."
---

# Setup check

Run every check, do not stop at the first failure, and print a table: check, PASS or FAIL, detail. Fix only the labels. Everything else is reported for Nikita.

1. **Settings.** First read the newest `SS Settings` note (label `SS/Settings`, if any) and run `ss.py load-settings` with its JSON as `overrides` (`{}` if none); an `error` is a FAIL for the note. Then read `${CLAUDE_PLUGIN_ROOT}/config/settings.json` with those overrides applied (`effective` in the output). Report `send_mode`, `paused`, `warmup_start_date` (FAIL if missing), `alert_email`, and the sending address. The sending domain is the part after `@` of the sending address.
2. **DNS** for the sending domain. Use `nslookup -type=txt <domain>` (or `dig +short txt <domain>`):
   - SPF: a TXT record starting `v=spf1` that includes `_spf.google.com`.
   - DMARC: `nslookup -type=txt _dmarc.<domain>`, a record starting `v=DMARC1`. WARN if `p=none` after the first month.
   - DKIM: `nslookup -type=txt google._domainkey.<domain>` (also try the selector Google Workspace shows in Admin). FAIL if no `v=DKIM1` record.
3. **Gmail connector** reachable, and it is the `.in` mailbox: look up the connected profile or search for one message. FAIL if it is any other mailbox, and in particular the `.com` one.
4. **Hiresome connector** reachable: run one small read (list recent hired applications).
5. **Apollo key**: `ss.py apollo` with `{"action": "search_orgs", "keywords": ["software"], "locations": ["India"], "headcount": [50, 500], "per_page": 1}`. PASS if it returns results; the key is injected outside the script, so do not try to read the variable.
6. **Scripts**: 
```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ss.py" today <<'JSON'
{"sent_today": 0, "drafted_today": 0, "followups_due": 0}
JSON
```
PASS if it returns JSON with `send_day`. FAIL on a missing module such as `holidays`.
7. **Labels.** Make sure these exist in the `.in` mailbox, creating any that are missing and listing what you created: `SS/Step-1`, `SS/Step-2`, `SS/Step-3`, `SS/Step-4`, `SS/Step-5`, `SS/Replied`, `SS/Interested`, `SS/Not-now`, `SS/Wrong-person`, `SS/OOO`, `SS/Do-not-contact`, `SS/Bounced`, `SS/Meeting`, `SS/Won`, `SS/Stopped`, `SS/Alerted`, `SS/Lessons`, `SS/Campaigns`, `SS/Settings`. Also one `SS/C-<slug>` label for each campaign (newest `SS Campaign <slug>` note per slug, plus `${CLAUDE_PLUGIN_ROOT}/config/campaigns.json`) whose status is `active`. Also check that `when_no_campaign` in settings is `wait` or `default`, and that campaigns parse (run `ss.py campaign` with `{"campaigns": [<parsed notes>], "counts": {}, "new_cap": 5}`; an `error` is a FAIL).
8. **Sending without approval.** Using the Gmail connector, send a short email from the `.in` mailbox to `alert_email`, subject `Stellaspire setup check <date>`, body "Setup check. If you read this, sending works." If it sends with no approval prompt, PASS. If it fails or waits for approval, FAIL and say clearly: "Scheduled runs will stop at this point. Fix the connector's approval setting before relying on send mode or on alerts." Do not retry in a loop.
9. **LinkedIn doc.** If `linkedin_doc_url` is set, open it through the Claude Docs connector: PASS if it's readable. If it's empty, create a doc titled "Stellaspire LinkedIn notes" with a one-line intro ("Connection notes to send by hand on LinkedIn. Newest day first."). Then ask Nikita: "Shall I save this doc link as your LinkedIn notes doc?" Only after an explicit yes, save it as in `/stellaspire-outreach:settings`: `ss.py settings-check` with the newest `SS Settings` overrides plus `linkedin_doc_url`, then send a new note-to-self with subject `SS Settings` and the full override JSON, labelled `SS/Settings`. Without a yes, WARN, not FAIL: notes go in the report until it's set.
10. **Firecrawl** (optional). If a Firecrawl tool is available, run one `firecrawl_scrape` on `https://stellaspire.com`: PASS or FAIL. If it isn't available, WARN: "research falls back to WebSearch and WebFetch".
11. Print the table, then a one-line verdict: ready for `draft` mode, ready for `send` mode, or not ready, with the failing checks.
