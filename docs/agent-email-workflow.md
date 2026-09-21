# Run the email classifier from Codex or Claude Code

The agent runs a Python command. That command calls Jev. The agent then summarizes the returned JSON. Jev is not the coding agent's replacement model.

## First, prove the command works

Complete the README setup, including the TypeSafe key, then run from the repository root:

```bash
.venv/bin/python -m jev_tutorial.email_cli data/emails.json
```

Input is a JSON array. Every email needs a unique string `id`, plus nonempty `subject` and `body` strings. The sample file contains five invented messages. The command sends only subject and body to TypeSafe; IDs are preserved locally to match the answers.

Category definitions live in `config/email-categories.json`. To try another policy:

```bash
.venv/bin/python -m jev_tutorial.email_cli data/emails.json --categories config/email-categories.json
```

The command emits a JSON array to stdout only after every email succeeds. On failure, stderr contains a short error and the exit status is nonzero. It does not emit a partially successful batch or silently classify failures as Other.

## Use it without installing anything

Open this repository in Codex or Claude Code and paste:

```text
Read skills/jev-email-triage/SKILL.md and follow it.
Classify data/emails.json. Show the returned category, confidence,
action-request probability, and review flag for each email ID.
Run the actual command; do not classify the messages yourself.
Do not access or modify my mailbox.
```

The agent needs access to the local Python environment and permission to reach TypeSafe. A browser-hosted or cloud task does not automatically inherit the key stored on your laptop. Configure its environment separately if you use one.

## Optional: install the project skill

Use the supplied skill without overwriting an existing installation. Run these commands from the repository root in bash or zsh.

For Codex:

```bash
mkdir -p .agents/skills/jev-email-triage
cp -n skills/jev-email-triage/SKILL.md .agents/skills/jev-email-triage/SKILL.md
```

Start a fresh task in the repository and select or explicitly name `jev-email-triage`. Codex reads repository skills from `.agents/skills`. [Official Codex skill documentation](https://developers.openai.com/codex/skills/)

For Claude Code:

```bash
mkdir -p .claude/skills/jev-email-triage
cp -n skills/jev-email-triage/SKILL.md .claude/skills/jev-email-triage/SKILL.md
```

In Claude Code, use `/jev-email-triage` and specify `data/emails.json`. If the skill does not appear, start a new session from this repository. [Official Claude Code skill documentation](https://code.claude.com/docs/en/skills)

Both installed copies point to the same repository command. Keep the working directory at the repository root. Installation is optional and has not been performed by the example itself.

## Fit it into an existing email routine

The integration boundary is a local JSON array. Your existing authorized email retrieval step can produce it, and your routine can match results back to messages by ID. Store real exports outside version control, for example under the ignored `local-data/` directory.

Start with a dry run that only displays suggestions. Finalize the categories and check a labeled sample before adding any mailbox changes. This repository supplies neither a mailbox connector nor an automatically scheduled routine. It does not change the existing routine.

Measure the whole routine if you compare it with its previous version. A cheaper classification request does not by itself prove that agent orchestration, retrieval, retries, and summary generation became faster or cheaper.
