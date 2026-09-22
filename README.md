# Build with Jev

Learn Noul, Choice, and Score in Python. Use them in a local customer support app, then reuse the approach to classify emails from Codex or Claude Code.

**Start with the [video walkthrough](docs/tutorial.md).** It follows the actual commands and files, with plain explanations you can show on screen.

## Set up

Python 3.10+ and a [TypeSafe API key](https://console.typesafe.ai) are required for live classification. From the repository root on macOS or Linux:

```bash
uv sync --locked
```

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first if needed. This creates `.venv` and installs the locked dependencies, including the development dependency `ipykernel` for notebooks. Select `.venv/bin/python` as your notebook interpreter. To omit development dependencies, use `uv sync --locked --no-dev` and run commands with `uv run --no-dev python` instead of `uv run python`.

Create a local `.env` file containing `TYPESAFE_API_KEY=your_key_here`, or export that environment variable. Examples load `.env`; exported values take precedence. Never commit a real key. Model calls send the sample input to TypeSafe.

## Follow the video

| Step | Command | What you learn |
| --- | --- | --- |
| Noul | `uv run python examples/01-noul.py` | Detect an explicit refund request |
| Choice | `uv run python examples/02-choice.py` | Select a support team |
| Score | `uv run python examples/03-score.py` | Assess impact using an ordered rubric |
| Combine | `uv run python -m jev_tutorial.triage` | Ask independent questions, combine answers in code |
| Build | `uv run python -m jev_tutorial.app` | Create, classify, and review tickets in a browser |
| Reuse | `uv run python -m jev_tutorial.email_cli data/emails.json` | Classify five synthetic emails as JSON |
| Evaluate | `uv run python -m jev_tutorial.evaluate` | Save decisions, errors, latency, and estimated cost for twelve tickets |

Open the support desk at [127.0.0.1:5050](http://127.0.0.1:5050). Tickets and human corrections persist in `instance/tickets.sqlite3`. A failed API call keeps the ticket and offers retry. This is a local teaching app, not a hosted service with authentication.

All thresholds are teaching values. Model confidence is not an accuracy guarantee. No example moves mail, executes refunds, or updates GitHub.

The email categories are **AI Engineer, Business Inquiry, Sponsorship, and Other**. Edit [their descriptions](config/email-categories.json); Business Inquiry is provisional. The [agent guide](docs/agent-email-workflow.md) shows the shared command and optional skill installation for Codex and Claude Code. The sample uses local JSON, not a live mailbox.

## Additional examples

The earlier examples remain available under `src/`. They load `.env` too.

| Script | Purpose |
| --- | --- |
| [01-classify-emails.py](src/01-classify-emails.py) | One email using the provisional categories |
| [02-classify-github-issues.py](src/02-classify-github-issues.py) | Suggest implementation risk |
| [03-prioritize-support.py](src/03-prioritize-support.py) | Score impact on work |
| [04-classify-documents.py](src/04-classify-documents.py) | Classify document text |
| [05-tag-feedback.py](src/05-tag-feedback.py) | Apply multiple independent tags |
| [06-filter-search-results.py](src/06-filter-search-results.py) | Filter three passages |
| [07-find-duplicate-issues.py](src/07-find-duplicate-issues.py) | Suggest duplicate reports |
| [08-showcase.py](src/08-showcase.py) | Original three-ticket combined demo |

The original showcase uses a simpler policy than the support app. The app also checks whether impact is stated. Use `jev_tutorial/classifier.py` when explaining the app's actual behavior.

## Check the code

```bash
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q examples jev_tutorial src
```

The automated tests use controlled responses to verify routing, persistence, failure recovery, corrections, and the email interface. They do not establish model accuracy. Run the evaluation separately for live model behavior.

More material: [use cases](docs/use-cases.md), [recording notes and sources](docs/recording-notes.md), [verification](docs/verification.md).
