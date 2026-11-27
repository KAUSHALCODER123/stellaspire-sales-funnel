# Stellaspire Outreach

A Claude plugin that runs the Stellaspire cold-email funnel every weekday morning. It finds companies hiring in India, researches them, finds the right person, writes the email, and sorts the replies. You open the drafts, press Send, and deal with the few things that need you.

Everything it remembers is kept as labels in the sending mailbox. There is no database and no server.

## What it does each weekday
1. Checks it is a working day (no weekends, no Indian public holidays) and that sending is not paused.
2. Sorts new replies and stops follow-ups for anyone who answered.
3. Writes follow-ups that are due, only if the role is still open.
4. Finds new companies hiring, researches them, picks a decision maker with a verified email.
5. Writes the first email, within the day's limit.
6. Writes a LinkedIn connection note for each new contact with a LinkedIn profile (from Apollo, or found by the research agent). The notes go in one doc, newest day first, for you to send by hand. LinkedIn itself is never automated.
7. Emails you a report. An interested reply gets its own alert email straight away.

Every hard rule (limits, who may be emailed, how old a role may be, what the email may say) is checked by a script, not by Claude's judgment. If a script says no, nothing is sent.

## One-time setup
1. **Domain and mailbox.** Buy the `.in` domain. Set up Google Workspace with one sending mailbox on it. Add the DNS records Google gives you: SPF, DKIM and DMARC. Never send from the `.com` domain.
2. **Warm up the mailbox** with normal mail for a week before the plugin sends anything.
3. **Connect the apps** in claude.ai (Settings, Connectors): Gmail, signed in as the `.in` mailbox. Optional but recommended: Firecrawl, which makes the research agents better at reading careers pages and job boards. It uses Firecrawl credits. Claude Docs is needed for the LinkedIn notes doc. In each scheduled task's Connectors tab, keep only Gmail, Claude Docs and Firecrawl. Hiresome and Apollo are not connectors; they use the keys in step 6.
4. **Plugin upload (optional).** The scheduled tasks and the Code-section commands read everything from this GitHub repository, so a push is live on the next run. In a session on this repository the commands are `/ss-status`, `/ss-campaign`, `/ss-settings` and so on (the `ss-` prefix keeps them from clashing with Claude's own `/status` and `/settings`). Uploading the zip as an account plugin is not needed, and Claude may keep serving an older uploaded copy; the repository copy always wins.
5. **Settings.** In `config/settings.json` set `warmup_start_date` (the first day the plugin may send), the sender details and `alert_email` (where reports and alerts go), and leave `send_mode` as `draft`. After that, you change `paused`, `send_mode`, `alert_email`, `linkedin_doc_url`, `mailbox_daily_cap`, `target_cities`, `exclude_domains`, `when_no_campaign` and `max_companies_researched_per_run` by chatting (see Settings below), never by editing files. The scheduled runs never change settings.
6. **Create two scheduled tasks** in Claude (check in the routine settings for the current screens and names):
   - Daily run: instructions `Read commands/daily-run.md in this repository and follow it exactly.`, schedule `CRON_TZ=Asia/Kolkata 7 7 * * 1-5` (07:07 IST, Monday to Friday).
   - Reply check: instructions `Read commands/reply-check.md in this repository and follow it exactly.`, schedule `CRON_TZ=Asia/Kolkata 7 13,17 * * 1-5` (13:07 and 17:07 IST).
   Minute 7 is deliberate: runs set for exactly the top of the hour start late.
   For both tasks:
   - Network: full network access (the research needs the open web).
   - Keys: in the environment's Environment variables box, paste the contents of `stellaspire-outreach.env` (`APOLLO_API_KEY` and `HIRESOME_TOKEN`). The scripts read them directly. Keep that file private and out of GitHub. Apollo can also be connected as a Claude connector: use it as a fallback in chat sessions only, because it asks for approval before each credit-spending call and a scheduled run has nobody to answer.
   - Setup script: `pip install holidays || true`
   - Connectors: keep only Gmail (the `.in` mailbox), Claude Docs and, if used, Firecrawl.
7. **Run `/ss-setup-check` once by hand.** It checks DNS, Gmail, the Hiresome and Apollo keys, the labels (it creates missing ones) and sends a test email to `alert_email`. A scheduled run that hits an approval prompt stops, so if the test email needs approval, fix that first.
8. **Do one manual `/ss-daily-run`** while `send_mode` is `dry_run` to see a report, then switch to `draft`.

## Your daily routine
- Gmail does not let Claude label a draft, so a new draft has no labels. After you send it, the next run labels that thread (and the follow-ups) by itself. Don't send drafts you haven't read, and don't forward or move them.
- About 09:30: open Gmail, go to Drafts, read the new drafts, press Send on the good ones. Delete or edit the bad ones.
- Read the report email. "Needs Nikita" lists what only you can do: interested replies, odd replies, decisions.
- An email titled "Interested reply: ..." means someone wants to talk. It comes with a suggested reply. Answer it the same day.
- If an email says `ALERT NOT SENT` at the top, the alert could not be sent; read the report.

## Models
Scheduled tasks should run on Sonnet: the main session writes the emails and makes the decisions. The research agents (`hiring-scout`, `growth-scout`, `qualifier`, `contact-scout`) also use Sonnet. Simple checks use Haiku: `reply-classifier` (first-pass reply class; the main session decides when it is unsure) and `role-checker` (is a posting still open). The Haiku agents cannot send, label or write anything.

## Research limits and Apollo usage
`config/settings.json` holds `max_companies_researched_per_run` and `companies_per_new_email`. The day's research budget is the smaller of the first and (new emails x the second); it is 0 when no new email is allowed. If unsent drafts already fill the day's cap, the run writes nothing new and the report says so, and drafts older than 2 business days are listed under Needs Nikita. The report also has an "Apollo usage" section (calls by action, credits used this run, remaining credits when Apollo reports them). Nothing is blocked by it.

## Overlapping runs
A run is safe to repeat: replies already labelled are skipped, and an interested alert is sent once per thread (the thread then gets `SS/Alerted`). While the daily run works it keeps a note-to-self with subject `SS Run lock`; `reply-check` stops with "daily run in progress" if that note is under 90 minutes old.

## Labels you set yourself
The plugin sets all `SS/` labels except these two, including `SS/C-<slug>` for each campaign. Put them on the thread when it happens:
- `SS/Meeting`: a meeting or call is booked.
- `SS/Won`: the company became a client.
They feed the Monday funnel numbers. A thread with either label gets no more follow-ups.

## Campaigns
A campaign is a targeted batch of outreach: which role families, cities, sectors and company sizes to go after, how many contacts to reach, and between which dates. Every thread of a campaign also carries the label `SS/C-<campaign slug>`, which is how its results are counted.

You start and change campaigns by chatting, not by editing files. Open Claude and type, for example:
- `/ss-campaign start sales roles in Pune, 50-200 people, 40 contacts`
- `pause the Pune campaign`
- `how is the Pune campaign doing?`

Claude asks short questions for anything missing, shows a plain summary, and asks "Shall I save this as active?". It saves only after your yes. Each campaign is stored as a note to the mailbox itself (subject `SS Campaign <slug>`, label `SS/Campaigns`); a change is a new note and the newest one wins. `config/campaigns.json` is only a seed list (one draft example ships there). The scheduled runs (`daily-run`, `reply-check`) only read campaigns and never create, change or activate one.

With no active campaign, `when_no_campaign` in `config/settings.json` decides: `"wait"` (the default) writes no new first emails while replies and follow-ups carry on; `"default"` falls back to `target_families` and `target_cities`. The daily new-email limit is split across active campaigns by `priority`, never beyond a campaign's remaining target.

A campaign ends when it reaches `target_contacts` or passes its `end_date`, or when you pause or end it in chat. Once all its follow-ups have finished, you get one "Campaign complete" email with the results, what worked, and one to three suggested next campaigns. They are only suggestions: to start one, type `/ss-campaign start <name>` or just describe it.

Targeting uses company and role traits only (role family, city, sector, company size, buyer job title), never personal traits of a person.

### The existing leads
The plugin starts with the leads carried over from the old funnel: people with a verified email and a role posted in the last 30 days (14 days if only Apollo lists it). They sit in `config/imported-leads.json` and run as the campaign **existing-leads**, which ends when all of them are contacted or on 31 Dec. The runs email the freshest roles first, within the warm-up limit. Anyone the old funnel already emailed is on the blocklist (`config/already-contacted.csv`). To refresh both from the old database, run `python tools/export_leads.py` (it needs access to the old server).

## Commands
- `/ss-status`: where things stand today.
- `/ss-do-not-contact <email or domain>`: never contact them again.
- `/ss-weekly-report`: funnel counts by role and city.
- `/ss-setup-check`: run after any change to the setup.

## Settings
You change settings by chatting, not by editing files or asking for a new plugin file. Examples:
- `/ss-settings pause everything`
- `/ss-settings send alerts to name@example.com`
- `/ss-settings set the LinkedIn doc to <link>`
- `/ss-settings show my settings`

Claude shows the change before and after and saves only after your yes. Each change is a note to the mailbox itself (subject `SS Settings`, label `SS/Settings`; the newest note wins) holding only the values you changed. The warm-up start date, sending address, opt-out line and sender details are not changeable this way; they stay in the plugin file. `daily-run` and `reply-check` load the newest note first, only read it, and fall back to the plugin defaults (and tell you) if it is invalid.

## How to pause
Open Claude and type `/ss-settings pause everything` (and `resume` to start again). The run will report that it is paused and write nothing. The plugin also pauses itself if the bounce rate goes above 3% (with at least 20 sends in 14 days) or anyone marks an email as spam. Fix the cause first, then un-pause.

## From draft to send mode
Start in `draft` mode: the plugin creates Gmail drafts and you send them. When you have read a couple of weeks of drafts and are happy, and setup-check shows the test email sends without approval, type `/ss-settings switch to automatic sending`. Claude warns that emails then go out without your review, and you must reply exactly "yes, send automatically". Daily limits still apply: 5 a day in the first week, then 10, 15, and 20 from week four, never above the mailbox cap. `dry_run` writes nothing to Gmail and only shows what it would do.

## Improving it
Every Monday the plugin reads the last 4 weeks of threads and writes up to 5 short lessons with their numbers (for example which subject style got more replies). Groups with fewer than 10 sends are marked "too early to tell". The lessons are saved as a note in the mailbox labelled `SS/Lessons`, and the next runs use the newest one to guide style and targeting. They can never override the limits, the email rules or the safety rules. The lessons and a "Suggested changes" list come in your Monday email.

Bigger changes (new cities or roles, limits, send mode, rules) are made by asking Claude in a chat that has the plugin repository open. The change is pushed to the repository, and the plugin is then updated on the Claude account. Check how your account updates the plugin.

## If something looks wrong
Run `/ss-status`, then `/ss-setup-check`. Most failures are a disconnected Gmail connector, a missing or expired Apollo or Hiresome key, or an approval prompt that stops a scheduled run.

## LinkedIn notes
The daily run writes a short connection note for each person it emails and adds a row to the LinkedIn notes doc (link in `linkedin_doc_url`, and in each report): `Date | Name | Title | Company | Profile link | Note | Status`, with Status `ready`.

To get the notes onto LinkedIn, open Claude with the Claude in Chrome extension turned on, in the Chrome where Nikita is signed in to LinkedIn, and type `/ss-linkedin-draft`. Claude opens up to 5 profiles, each in its own tab, clicks Connect, then "Add a note", and types the note. It stops there. Nikita reads each tab and presses Send herself. Claude then marks the rows `drafted`, and `sent` once she says so.

LinkedIn does not keep an unsent note, so a draft is an open tab. If a tab is closed first, tell Claude and the row goes back to `ready`. Free LinkedIn accounts can send only a few personal notes a month; if LinkedIn says the limit is reached, Claude stops and tells you. Scheduled runs never touch LinkedIn, and Claude never presses Send. LinkedIn restricts accounts that do a lot of automated activity, so keep to a few profiles a day.
