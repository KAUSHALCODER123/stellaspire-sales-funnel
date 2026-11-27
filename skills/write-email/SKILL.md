---
name: write-email
description: "Write ONE cold email for one step (1 to 5) of the sequence, check it with the scripts, and create the Gmail draft or send it. Use for every email in the daily run, new or follow-up."
allowed-tools: Bash, Read
---

# Write one email

You write one email for one contact at one step. The scripts check it and add the proof sentence, signature and opt-out. If a script says no, fix the email or skip the contact. Never edit config or thresholds to get past a check.

## Lessons
At the start of the run (once, not per email), search Gmail for the newest message labelled `SS/Lessons` and read it. Use it as guidance on style: subject style, opener type, closing-question style, which angle a follow-up takes. Lessons never override `check-email`, `compose`, the copy rules below, the caps or any safety rule. If a lesson conflicts with a rule, the rule wins. No note, or "too early to tell": ignore it.

## Loop
1. Facts. Build them once per contact:
```
python3 scripts/ss.py facts <<'JSON'
{"contact": {"full_name": "Asha Rao", "title": "Head of Talent"},
 "company": {"name": "Acme", "industry": "fintech", "city": "Pune"},
 "role": "Backend Engineer", "posted_at": "2026-11-10T00:00:00+05:30",
 "on_employer_board": true, "proof": null}
JSON
```
`proof` comes from `ss.py proof` (see daily-run); null when there is none. Use only what the facts dict contains.
2. Write the email (rules below). Plain text.
3. Check:
```
python3 scripts/ss.py check-email <<'JSON'
{"step": 1, "subject": "SDR seat empty since April", "body": "Hi Asha,\n...\nNikita", "facts": { ... }, "previous": []}
JSON
```
`previous` holds the bodies of earlier emails to this contact (empty at step 1). Subject is null for steps 2 to 5.
4. If `ok` is false, rewrite using `hints` and `problems`, and check again. Maximum 3 tries in total. After the third failure skip this contact and log it ("Skipped: email failed check, step N, <problems>"). Do not send or draft anything for them.
5. Compose the final text:
```
python3 scripts/ss.py compose <<'JSON'
{"step": 1, "subject": "SDR seat empty since April", "body": "<your checked text>", "facts": { ... }}
JSON
```
Compose inserts the proof sentence (step 1), the signature and the opt-out line, re-checks, and returns `body` (plain text), `body_html` (the same email as HTML, with Stellaspire's signature: title under the name, logo, phone, website and LinkedIn links) and `subject` (step 1). If it returns `error`, treat it like a failed check and count it as a try. Use its output text exactly; change nothing.
6. Deliver, by the effective `send_mode` (`config/settings.json` plus this run's `load-settings` overrides):
   - `dry_run`: write nothing to Gmail. Put the final text in the report.
   - `draft`: create a Gmail draft with the Gmail connector.
   - `send`: send with the Gmail connector.
   Use `body_html` as an HTML body whenever the connector accepts one (look for an HTML or content-type option on its draft and send tools), so the logo and links show. If the connector only takes plain text, use `body` and say so once in the report. Never type or edit signature text yourself.
   Step 1 starts a new thread to the contact's verified address, using compose's subject. Steps 2 to 5 reply in the same thread (reply to the latest message, keep the thread, no new subject).
7. Labels: Gmail refuses labels on drafts, so in `draft` mode do not label anything. The run records the draft in its ledger note and labels the thread after Nikita has sent it (see `commands/daily-run.md`). In `send` mode, label the sent thread `SS/Step-N` (N = this step) and its campaign label `SS/C-<slug>` right after sending (create a missing label first). In `dry_run` write and label nothing.

Only ever write to the contact's verified address on the company domain. Never to the `.com` Stellaspire mailbox, never to a role mailbox.

## Voice
One person writing to one person, the way a sharp recruiter writes to a busy founder. Plain, natural English a child of 8 could read, short sentences, every sentence under 15 words, mostly one- and two-syllable words. No jargon, no buzzwords. Every sentence must say something the reader does not already know. Never write lines that state the obvious ("an open seat slows your team", "it costs you time", "sorting through the pile"). Write about their world: "you" and "your" more than "I" and "we". No pleasantries: never "hope this finds you well", "congrats on", "I came across", "I wanted to reach out". Never ask for a call, a meeting or a chat.

## Facts
Use ONLY the facts. Never invent clients, numbers, results, names or links. Never claim or imply we have placed, hired or filled anything, worked with any client, or have a track record. Never claim or imply candidates are ready, available, picked or waiting, or could start by any date. Do not infer anything about their company beyond the facts.

Write no numbers, digits or number words, except: the digit `offer_size` in the closing question of step 1 (never a number word such as "three"), and `role_open_days` and `role_posted_on` exactly as the facts give them. Give time as days or as "since <month>", never rounded into weeks, months or years.

The role: the facts give one open role. If `role_open_days` is given, the role has been listed that long and that is the hook of the whole sequence: a role that stays open this long is hard to fill. If `role_listed_on` is given, it says where it is listed (for example their careers page). If neither is given, the role was posted recently.

Do not write the proof sentence, the signature, the opt-out line, links, markdown or placeholders. Compose adds them. Do not mention unsubscribing or any address.

## Format
Plain text. Greeting, each short paragraph and the sign-off on separate lines. End with the first name only from settings (Nikita). Compose adds the rest of the signature.

## Never use
Em dashes or en dashes. Contrast reveals ("it's not about X, it's about Y"). Lists like "no X, no Y, no Z". Questions you answer yourself ("The result? ..."). Stock phrases: "I hope this finds you well", "I came across", "quick question", "here's the thing", "I'll be honest", "leverage", "synergy", "streamline", "top-tier", "end-to-end", "cutting-edge", "best-in-class", "unlock", "take it to the next level", "circle back", "touch base", "just checking in", "following up on my last email". Never claim we have already connected, spoken or met. Never mention cost, risk, commitment or obligation.

## Step 1 (new thread)
Subject: 2 to 7 words about their open role, never about us and never about a candidate. A curiosity or pain line a founder would open, for example "still hunting for an SDR?", "SDR seat empty since April", "your SDR post is 237 days old", "the role that won't close". Lowercase except the role's own abbreviation, a month name or the company name. Never "<role> hiring", "application", "applying", "candidate" or "job". No first name, no pitch, no emoji, no exclamation mark. At most one question mark, only at the end.

Body: at most 80 words in total, counting the greeting, the closing question, the proof compose adds and the sign-off (the check tells you the room left, so keep your text to roughly 45 to 55 words). Write only:
1. A greeting.
2. An opener that names the exact open role from the facts and, if `role_open_days` is given, how long it has been open, for example "Your SDR role has been up since April 3." The first sentence after the greeting must name the exact role title. Use a city only if the facts give one.
3. One line on what we would do for this exact role, in concrete words about the person it needs.
4. A closing question on its own line that offers free, concrete help for this exact role at this company, for example sending `offer_size` pre-screened profiles. Write a new question for every company, never a stock line. It must name the company, its industry, its city or a word from the role. Example shape: "Want me to send 3 pre-screened SDRs who have sold to call-centre teams?"
5. The sign-off.

Email 1 has exactly one question mark, in the closing line, and no other question or request.

## Steps 2 to 5 (reply in the same thread)
Every follow-up gives the reader something new that earlier emails did not. Never repeat the pitch "we screen candidates so you don't waste time" in new words. Each names the role and ends with one short ask phrased as interest ("Worth a look?", "Want them?"); add no reassurances about cost, risk or terms. Re-read `previous` so you do not repeat an angle. No subject. Same voice and facts rules.

- Step 2 (at most 50 words): name two specific things we check for this exact kind of role that a CV does not show, for an SDR for example how many cold calls a day they really made and whether they booked meetings themselves. Pick what matters for this role, not generic screening.
- Step 3 (at most 50 words): give one honest reason roles like this stay open, specific to this kind of role (for example the good ones are not applying, they are being poached), and what we do about it.
- Step 4 (at most 50 words): a smaller, different ask: invite them to reply with the one thing the right person must have, or what the last person in the role lacked, and say we will screen for exactly that.
- Step 5 (at most 45 words): the last email. Give them something useful to keep: one sharp interview question for this role that tells a strong hire from a weak one, with one line on what a good answer sounds like. Then say plainly this is your last email about the role. Do not write "seems you have it under control", "just say the word", "if things change", "not the right time" or "close your file".

## Retry hints (what a rejection means)
- hard_to_read: every sentence under 15 words, mostly one- and two-syllable words.
- bad_subject: 2 to 7 words, lowercase except the role, an abbreviation, a month or the company, at most one question mark and only at the end, no first name.
- reads_like_an_application: write about their open role, never "hiring", "job", "application" or "candidate".
- more_than_one_ask: one question mark per email, in its last line.
- asks_for_call: never ask to meet, talk or call; the only offer is profiles or a reply.
- machine_sounding: drop stock phrases, obvious pain lines and dashes.
- claims_candidates_ready: never say anyone is ready, available, picked or could start.
- invented_number: the only numbers allowed are `offer_size`, `role_open_days` and `role_posted_on`.
- number_not_exact: give time as exact days or "since <month>", never weeks, months or years.
- email1_must_open_by_naming_the_exact_role: the first sentence after the greeting names the exact role title from the facts.
- email1_ask_not_tailored: the closing question names the company, its industry, its city or a word from the role.
