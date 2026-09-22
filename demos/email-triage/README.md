# Email triage with Jev

Python fetches a batch of emails, asks Jev for a category and whether action is
needed, and returns a report. Codex runs the script through a skill and presents
the results. The same command works unattended after Gmail authorization.

The video demo uses fictional emails with real API calls. No Google setup or
personal email access is needed for demo mode. There is no dashboard or agent
processing loop. Nothing sends mail or changes the inbox.

## Run the demo

From the repository root, with uv installed and your TypeSafe key in `.env`:

```bash
uv run demos/email-triage/scripts/triage.py --demo --env-file .env
```

Eight emails cover sponsorship offers, consulting, community support, a completed
sponsorship, a newsletter, a vague collaboration, corporate training, and a
marketing message containing instructions to manipulate classification.
Results are real predictions; expected behaviour is not hardcoded.

The first run saves results locally. A second run reuses them and reports zero
new API calls. To deliberately measure a fresh run, supply a new file path:

```bash
uv run demos/email-triage/scripts/triage.py --demo --env-file .env --cache /tmp/email-triage-recording-01.sqlite3
```

Use a new filename for another fresh run. That makes more paid API calls.

## Install the skill

Copy this directory to `~/.agents/skills/email-triage`. Keep an existing installation
backed up if you have customized it. Put your TypeSafe key in
`~/.config/email-triage/.env` with owner-only permissions, or set
`TYPESAFE_API_KEY` in the process environment. An explicit `--env-file` is supported.
Never put credentials in the skill package or commit them.

```text
$email-triage Run the demo inbox and show the classification cost.
Use the TypeSafe key from this repository's .env.
```

Open a new Codex session if needed to discover the installed skill. Codex reports
the script's results; it does not choose different categories or hide failures.

## Categories and attention

| Category | Meaning |
| --- | --- |
| sponsorship | Paid promotion in your videos, newsletter, or other content |
| business_enquiry | Consulting, implementation, company training, speaking, and client follow-ups |
| ai_engineer | AI Engineer community membership, access, and member support |
| other | Newsletters, generic sales pitches, personal mail, and other messages |

Each message gets one Choice answer and a separate Noul probability that the
recipient needs to reply, decide, or do something. A sponsorship can need action
or simply confirm that payment is complete. A newsletter's "read more" is not
an outstanding task. Edit the criteria in `scripts/triage.py` for your business.

A category probability below 80% requires review. Action probability at least
80% means needs attention; at most 20% means no action; between them means review.
These are teaching defaults, not validated accuracy guarantees. Decisions are
based on a single message, including any quoted history it contains. The script
does not fetch full threads or know whether you replied elsewhere. These flags
are triage suggestions, not a verified list of outstanding obligations.

## Cost and timing

The JSON report includes API-reported input tokens for new successful calls.
Estimated classification cost is:

```text
input tokens / 1,000,000 × $0.042
```

That is the [published price](https://docs.typesafe.ai/models) verified on
2026-09-22 for `jev-1.13.0`; output tokens are free at that price. The configured
price and verification date appear in every report. Update `PRICE` if it changes.
This is a usage estimate, not a billing statement. It excludes Codex summaries,
Gmail, hosting, and failed calls whose usage was not returned. If a call fails or
usage is missing, the full estimated cost is null and the known subtotal is shown.

Cached rows retain original token counts, but add no new usage to the run total.
`elapsed_seconds` covers cache and classification work; `total_elapsed_seconds`
also includes fetching. Neither is a pure model-latency benchmark.

## Connect Gmail, optionally

Follow Google's [Python Gmail setup](https://developers.google.com/workspace/gmail/api/quickstart/python):
enable the Gmail API in a Google Cloud project, configure OAuth consent and test
users as appropriate, and download a **Desktop app** OAuth client JSON. This
requires no Cloud Run deployment or Pub/Sub. Keep the client file outside the repo.

Authorize once in your own terminal:

```bash
uv run demos/email-triage/scripts/authorize.py --client-file /absolute/path/to/client.json
```

The browser asks for read-only Gmail access. Authorization is saved with owner-only
permissions in `~/.config/email-triage/gmail-token.json`. Only run this interactive
step deliberately. A scheduled run never launches authorization. Google OAuth
testing configurations may require reauthorization; check your app's consent
configuration before treating it as an unattended production service.

```bash
uv run demos/email-triage/scripts/triage.py --gmail --days 7 --limit 50 --env-file .env
```

This sends sender, subject, and message body to TypeSafe. It fetches up to the
limit from the requested period, excluding sent mail, drafts, spam, and trash.
It includes archived incoming messages, not just Inbox. Pagination continues up
to the limit; `more_messages_available` signals a partial window. This bounded
batch tool is not a guaranteed complete mailbox synchronizer. Increase the limit
up to 100 or narrow the period; high-volume inboxes need a persistent scan cursor
before using this as their only triage system.

MIME decoding prefers plain text and falls back to HTML text. It does not load
remote images, follow links, or send attachments to Jev. Empty or oversized inputs
are rejected for review rather than silently truncated. JSON-encoded messages
must fit within 24,000 characters.

## Automations

After authorization, an automation can run the same skill. A suggested prompt:

> Run $email-triage against my connected Gmail for the last 2 days, up to 100 messages.
> Use the existing credentials and cache. Report newly classified sponsorships,
> business enquiries, messages needing attention or review, errors, and Jev usage
> cost. If only cached messages remain and there are no errors or partial-window
> warnings, stay quiet. Never change my inbox or start interactive authorization.

This repository does not create a schedule. An overlapping lookback helps catch
messages between runs; the cache avoids repeated classification. It is not a
replacement for checking the partial-window flag or expired credentials.

## Storage, failures, and tests

SQLite stores message fingerprints, model outputs and original usage, not subjects,
senders or bodies. Reports do contain subjects and senders, so don't show Gmail
mode on camera. Demo and Gmail/account namespaces are separate. Changing the
message, criteria, model, or thresholds creates a new cache entry. Concurrent runs
using the same database serialize; a busy second run exits with a setup error.
Failures are not cached, so rerunning retries them. Automatic SDK retries are
disabled to make call attempts visible. An interrupted process can lose uncommitted
cache entries after paid calls; subsequent calls can incur additional usage.

```bash
uv run --with typesafe-sdk==0.7.0 --with python-dotenv==1.2.1 --with google-auth-oauthlib==1.2.2 python -m unittest discover -s demos/email-triage/tests -v
```

Exit 0 means the batch completed, 1 means individual failures or rejected messages,
and 2 means setup, fetching, or processing could not complete. No path writes to
Gmail. Inspect structured errors before retrying; never interpret failures as
"no emails need attention".
