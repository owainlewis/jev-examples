# Jev examples

Three small Python examples and a working ticket queue.

| File | What it shows |
| --- | --- |
| [src/01-noul.py](src/01-noul.py) | Noul: the probability of a yes/no answer |
| [src/02-choice.py](src/02-choice.py) | Choice: pick a team from named categories |
| [src/03-score.py](src/03-score.py) | Score: assess impact against an ordered rubric |
| [docs/VIDEO.md](docs/VIDEO.md) | The video walkthrough, from the first API call to the app |
| [demos/support-desk](demos/support-desk/README.md) | Python, React, and SQLite ticket queue with automatic department and priority classification |

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

Read [the video walkthrough](docs/VIDEO.md) for the explanation and recording order.
