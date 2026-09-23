# Jev examples

Three small Python examples and a working ticket queue.

| File | What it shows |
| --- | --- |
| [src/01-noul.py](src/01-noul.py) | Noul: the probability of a yes/no answer |
| [src/02-choice.py](src/02-choice.py) | Choice: pick a team from named categories |
| [src/03-score.py](src/03-score.py) | Score: assess impact against an ordered rubric |
| [docs/video.md](docs/video.md) | Tutorial covering the Python examples, support app, and Codex router |
| [demos/support-desk](demos/support-desk/README.md) | Python, React, and SQLite ticket queue with automatic department and priority classification |
| [demos/codex-router](demos/codex-router/README.md) | Shareable skill: Jev selects a model and Codex creates a new task |
| [demos/trading-sim](demos/trading-sim/README.md) | Live prices, Jev buy/hold/sell decisions, and a simulated portfolio |

## Issue readiness skill

[Install and try issue-ready](demos/issue-ready/README.md) to assess GitHub issues with Jev and apply readiness labels. Includes local examples for rehearsing the demo.

## Email triage skill

[Try email-triage](demos/email-triage/README.md): Python classifies fictional or read-only Gmail messages with Jev, caches results, and reports probabilities and estimated API cost. Codex presents the report through a shareable skill.

## Run the Python examples

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). From this folder:

```bash
uv sync --locked
cp .env.example .env
```

Add your TypeSafe API key to `.env`:

```dotenv
TYPESAFE_API_KEY=your_key_here
```

Then run any example:

```bash
uv run python src/01-noul.py
uv run python src/02-choice.py
uv run python src/03-score.py
```

Each script makes a real call to Jev using an invented ticket. Python dependencies are managed by `pyproject.toml` and `uv.lock`; no package installation is needed inside `src/`. The development group includes `ipykernel` for running the examples in an editor. Use `.venv/bin/python` as the interpreter. Use `uv sync --locked --no-dev` and `uv run --no-dev python src/01-noul.py` if you do not need it.

## Run the support app

Follow [the app setup](demos/support-desk/README.md). The demo has its own Python environment and frontend dependencies. Creating a ticket automatically classifies department and priority, shows the probabilities, and flags uncertain results for review.

Read [the tutorial](docs/video.md) for setup, examples, and explanations.
