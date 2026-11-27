---
description: "Never contact an email address or a whole domain again. Labels matching threads and records the value in the mailbox."
argument-hint: <email-or-domain>
---

# Do not contact

Argument: `$ARGUMENTS`, one email address or one domain. If empty or not one value, ask for it and stop.

The plugin directory is read-only, so do not edit any CSV. The list lives in Gmail.

1. Normalise the value: lowercase, strip `mailto:`, spaces and a leading `@`. An address contains `@`; otherwise it is a domain.
2. With the Gmail connector, find every thread with a participant matching the address (or any address at the domain). Create the label `SS/Do-not-contact` if missing and add it to each. Also add `SS/Stopped` so no follow-up goes out.
3. Create and send an email from the `.in` mailbox to itself, subject `SS DNC <value>`, one-line body "Do not contact <value>. Added <date>.", labelled `SS/Do-not-contact`. This keeps the value even when no thread exists. Check first that a note with this subject does not already exist; if it does, do not add another. If `send_mode` is `dry_run`, only say what you would do.
4. Print what you labelled and the note you created.
