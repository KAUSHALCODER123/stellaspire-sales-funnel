---
description: "Never contact an email address or a whole domain again. Labels matching threads and records the value in the mailbox."
argument-hint: <email-or-domain>
---

# Do not contact

> **Where this runs.** This file runs from the repository checkout, which is the current directory: scripts are `scripts/ss.py`, settings and lists are in `config/`. When a step says to run a skill or agent of this plugin, open its file in this repository (`skills/<name>/SKILL.md` or `agents/<name>.md`) and follow it. For an agent, start a subagent with that file's text as its instructions, on the model named in its header. Ignore any other installed copy of the stellaspire-outreach plugin: it may be out of date.

Argument: `$ARGUMENTS`, one email address or one domain. If empty or not one value, ask for it and stop.

The plugin directory is read-only, so do not edit any CSV. The list lives in Gmail.

1. Normalise the value: lowercase, strip `mailto:`, spaces and a leading `@`. An address contains `@`; otherwise it is a domain.
2. With the Gmail connector, find every thread with a participant matching the address (or any address at the domain). Create the label `SS/Do-not-contact` if missing and add it to each. Also add `SS/Stopped` so no follow-up goes out.
3. Create and send an email from the `.in` mailbox to itself, subject `SS DNC <value>`, one-line body "Do not contact <value>. Added <date>.", labelled `SS/Do-not-contact`. This keeps the value even when no thread exists. Check first that a note with this subject does not already exist; if it does, do not add another. If `send_mode` is `dry_run`, only say what you would do.
4. Print what you labelled and the note you created.
