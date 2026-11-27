---
description: "Prefill LinkedIn connection notes in your own Chrome with Claude in Chrome: a few profiles at a time, each in its own tab, nothing sent."
argument-hint: "[how many, up to 5]"
---

# LinkedIn drafts

> **Where this runs.** This file runs from the repository checkout, which is the current directory: scripts are `scripts/ss.py`, settings and lists are in `config/`. When a step says to run a skill or agent of this plugin, open its file in this repository (`skills/<name>/SKILL.md` or `agents/<name>.md`) and follow it. For an agent, start a subagent with that file's text as its instructions, on the model named in its header. Ignore any other installed copy of the stellaspire-outreach plugin: it may be out of date.

Run the `linkedin-draft` skill. If `$ARGUMENTS` is a number from 1 to 5, do that many profiles; otherwise do up to 5.

This is for a session with Claude in Chrome, in the Chrome where Nikita is signed in to LinkedIn. Follow the skill's hard rules exactly: you fill in the notes, Nikita presses Send.
