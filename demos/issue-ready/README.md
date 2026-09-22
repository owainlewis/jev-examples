# Issue readiness with Jev

A shareable Codex skill that reads a GitHub issue and labels whether its written
requirements are clear enough for an agent to start. Works in the CLI and desktop:
it uses `gh`, `uv`, and the TypeSafe API, with no desktop-only tools.

## Setup

Install uv and GitHub CLI, then authenticate with `gh auth login`. You need issue
write access to apply labels. Copy the skill into your personal skills folder:

```bash
mkdir -p ~/.agents/skills/issue-ready
cp -R demos/issue-ready/. ~/.agents/skills/issue-ready/
mkdir -p ~/.config/issue-ready
test -e ~/.config/issue-ready/.env || install -m 600 /dev/null ~/.config/issue-ready/.env
```

The last command creates an empty key file; skip it if your file already exists.
Add `TYPESAFE_API_KEY=your_key_here` to that file in your editor. An environment
variable takes precedence. Never commit the key. Open a new Codex session if the
installed skill is not available in the current one.

## Demo

Start with two local examples. These make real paid Jev calls but do not use or
change GitHub. From the repository root:

```bash
uv run demos/issue-ready/scripts/classify.py --file demos/issue-ready/examples/vague.json --env-file .env
uv run demos/issue-ready/scripts/classify.py --file demos/issue-ready/examples/clear.json --env-file .env
```

The vague example omits retry behavior; the clear example defines it. Outputs
are model results, not scripted labels. Unexpected results are worth discussing.

Then use a real open issue you own:

```text
$issue-ready https://github.com/OWNER/REPO/issues/123
```

To inspect without changing labels:

```text
$issue-ready Preview https://github.com/OWNER/REPO/issues/123 without changing it.
```

You can also call the script directly with `--issue URL`; add `--apply` to label.
Improve the issue's requirements and rerun to show the label changing. The skill
does not create sample issues, post comments, or start implementation.

## What Jev checks

Three Noul questions run against the title and body in one request:

| Check | A yes means |
| --- | --- |
| Clear request | The change and scope are described |
| Testable outcome | There are observable completion conditions |
| Unresolved decisions | A material behavior or product decision is missing |

Python selects the label:

- `needs-clarification`: clear request or testable outcome is at most 20%, or unresolved decisions is at least 80%.
- `agent-ready`: clear request and testable outcome are at least 80%, and unresolved decisions is at most 20%.
- `needs-review`: everything else.

A clear blocker takes precedence over uncertainty on another check. Probabilities
are not multiplied. These thresholds are teaching defaults, not measured accuracy.
Jev does not return an explanation; Codex can suggest improvements separately.

## Boundaries and failures

Only issue title and body go to TypeSafe. Comments, linked specs and repository
code are not assessed. Private issue text is also sent when you supply a private
issue URL. Inputs over 24,000 serialized characters are rejected, not truncated.
Pull requests and closed issues are rejected. The pinned model is `jev-1.13.0`.

A failed Jev call or invalid probability does not change GitHub. Before applying,
the script checks that the issue has not changed. It adds the new label first,
then removes only its other readiness labels. Unrelated labels are preserved.
These GitHub operations are not atomic: concurrent edits or network failures may
leave multiple readiness labels. The script reports failure; inspect and rerun.
Existing repository label descriptions and colors are preserved.

## Tests

```bash
uv run --with typesafe-sdk==0.7.0 --with python-dotenv==1.2.1 python -m unittest discover -s demos/issue-ready/tests -v
```
