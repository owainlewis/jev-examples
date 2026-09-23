# Feedback Lens

A local browser app that turns one customer message into three structured Jev answers. Inspect the full distributions and change the theme review threshold without another API call.

| Question | Jev type | What you see |
| --- | --- | --- |
| What is it about? | Choice | Reliability, usability, new capability, pricing, or other, with each probability |
| Can a team act on it? | Noul | Probability that a specific problem or desired change is stated |
| How much is work blocked? | Score | A weighted position on a 0–2 rubric, plus probabilities for every level |

All three questions run together against the same feedback in **one real API request**. Examples only fill the editor. There are no simulated results or generated explanations in the app.

## Run locally

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/getting-started/installation/). From the repository root:

```bash
cd demos/feedback-lens
uv sync --locked
cp .env.example .env
```

Put your TypeSafe key in the demo's `.env` file:

```dotenv
TYPESAFE_API_KEY=your_key_here
```

Start the app:

```bash
uv run --locked uvicorn backend.app:app --host 127.0.0.1 --port 8017
```

Open [Feedback Lens](http://127.0.0.1:8017). HTML, CSS, JavaScript, and the API come from the same server. No Node installation or frontend build is needed to run it. The header confirms that a key is configured; it does not validate the key until you submit feedback.

To use an existing credential file instead of copying it:

```bash
FEEDBACK_LENS_ENV=/absolute/path/to/.env uv run --locked uvicorn backend.app:app --host 127.0.0.1 --port 8017
```

Exported environment variables take precedence over the file. Restart the server after changing credentials. Use one server worker: the guard against simultaneous API calls is per process.

## A two-minute walkthrough

1. Choose **A broken export**. It fills fictional feedback with a working CSV workaround. Click **Analyze feedback** and inspect all three answers.
2. In **Theme review threshold**, use the slider or arrow keys. The rule updates locally. Below the threshold means review; equality passes. The threshold applies only to Choice, not Noul or Score.
3. Replace the workaround sentence with “I have no workaround and cannot finish the report.” Editing clears the old result so it cannot be mistaken for analysis of the new text. Submit again and compare impact.
4. Try **Look past keywords**. It mentions pricing but asks for a usability change. Inspect what Jev actually returns.
5. Try **Too little context**. Do not expect ambiguity to guarantee low probability. Expand **The questions behind the results** to see every instruction and rubric.

## How to read the results

The app picks the theme with the largest category probability. The review rule uses that unrounded value, not the SDK's separate `confidence` statistic. Percentages display one decimal place, so a displayed 80.0% can still be just below an 80% threshold. The initial 80% threshold is a teaching choice, not a calibrated guarantee of correctness. Passing the rule does not trigger an external action.

Noul is the probability of a **yes** answer. The No bar is its complement, `1 - p(yes)`. A specific request can be actionable while still difficult or inappropriate to implement. This question does not judge feasibility.

The impact rubric is ordered: **0** means no blockage is stated, **1** means work is slowed or a workaround is needed, and **2** means work cannot be completed with no stated workaround. The Score is the probability-weighted average of these levels. For example, probabilities of 0.1, 0.6, and 0.3 yield `0 × 0.1 + 1 × 0.6 + 2 × 0.3 = 1.2`. That is an illustrative calculation, not a captured model result. A fractional Score is not a percentage. Missing evidence of blockage does not prove there is no blockage.

Probabilities are model judgments, not observed accuracy. The model can be confidently wrong. Prompts ask Jev to treat feedback as data; this is not a guarantee against misleading or adversarial text.

## Errors, privacy, and limits

- Feedback is sent to TypeSafe's API. Use fictional or otherwise approved text. The key is read only in Python and never returned to the browser.
- The app does not write input or results to disk or browser storage. Reload clears them. This does not make claims about TypeSafe's data retention.
- Requests time out in the SDK after 30 seconds without automatic retry. The browser stops waiting after 45 seconds. A timed-out request can still count toward provider usage. Retry is an explicit new request.
- Errors preserve the current text and offer **Retry analysis**. The public message does not expose provider exception text. For a provider failure, check the key, account balance, and connection. Missing setup disables submission and offers **Reconnect to server** after a restart.
- Inputs are limited to 6,000 characters. One request can run per server process. Extra concurrent requests receive HTTP 409.
- Keep the server bound to `127.0.0.1`. This is a local demo with no user authentication. Host validation, same-origin checks, a required custom header, and no CORS permission protect against ordinary cross-site browser requests. They do not make it suitable for public hosting.
- Only `frontend/` is served as static content. Dotenv files and backend files are outside that directory. Responses use a restrictive content security policy and are not cached.

## Verify

From this demo folder, with development dependencies installed by `uv sync --locked`:

```bash
uv run --locked python -m unittest discover -s tests -v
uv run --locked ruff check backend tests
uv run --locked ruff format --check backend tests
```

JavaScript checks require Node 22+:

```bash
node --test tests/policy.test.mjs
node --check frontend/app.mjs
node --check frontend/policy.mjs
```

Optional frontend formatting check (pinned Prettier):

```bash
npx --yes prettier@3.8.1 --check 'frontend/*.{html,css,mjs}' 'tests/*.mjs'
```

Unit tests use explicitly injected test responses and never spend API credits. Live browser checks and acceptance evidence are recorded in [verification](docs/verification.md). The [task](docs/task.md) defines scope and acceptance criteria.

## Code map

- `backend/analyzer.py`: questions, fictional examples, SDK request, and response validation.
- `backend/app.py`: setup, HTTP boundaries, concurrency guard, and static serving.
- `frontend/app.mjs`: editor, request lifecycle, results, and rubric rendering.
- `frontend/policy.mjs`: display labels and the local theme review rule.
- `frontend/style.css`: responsive layout, focus, and reduced motion support.

The app pins the repository's `typesafe-sdk==0.7.0` and `jev-1.13.0` model. Dependencies are isolated from the other demos.
