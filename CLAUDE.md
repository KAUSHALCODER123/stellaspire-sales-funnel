# Stellaspire outreach: how to work in this repository

This repository runs Stellaspire's daily cold-email funnel (see README.md). It is the live version. Ignore any installed copy of a "stellaspire-outreach" plugin or its skills: it can be out of date.

Paths are relative to the repository root: scripts are `scripts/ss.py`, settings and lists are in `config/`.

When the user asks for one of these, open the file and follow it exactly. Plain English is enough; the user does not need to name the file.

| The user wants | File |
|---|---|
| How the funnel is doing, today's numbers, drafts waiting | `commands/status.md` |
| Start, change, pause, end or list a campaign | `commands/campaign.md` |
| Pause or resume everything, show or change settings, switch to automatic sending | `commands/settings.md` |
| Never contact a person or a company again | `commands/do-not-contact.md` |
| The weekly results | `commands/weekly-report.md` |
| Check that the setup works | `commands/setup-check.md` |
| Fill in LinkedIn connection notes in Chrome (needs Claude in Chrome) | `commands/linkedin-draft.md` |
| Run the daily outreach now | `commands/daily-run.md` |
| Check replies now | `commands/reply-check.md` |

Rules that always apply:
- Settings and campaigns are saved in the mailbox through `commands/settings.md` and `commands/campaign.md`, only after the user says yes. Never edit files in `config/` to change how the funnel behaves.
- Nothing is sent to a prospect unless `send_mode` is `send`. Drafts are for Nikita to read and send.
- If a script says no, do not do it.
