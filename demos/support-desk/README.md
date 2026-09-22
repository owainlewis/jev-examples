# Jev Support Desk

A standalone Python + React + SQLite demo for showing **Choice, Noul, Score, and Combined** on the same customer support ticket. The tutorial examples elsewhere in this repository are separate; this app imports none of them.

## Start the demo

Requires Python 3.11+ and Node 22.12+ (or Node 24).

From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Put your TypeSafe key in `.env`. The backend reads this folder's `.env`, not the tutorial's environment file. An exported `TYPESAFE_API_KEY` takes precedence. Restart the backend after changing it.

Build the frontend:

```bash
cd frontend
npm ci
npm run build
cd ..
```

Start the app:

```bash
uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Four synthetic tickets are created on first startup. Every classification calls Jev; changing mode does not. Each click uses your TypeSafe account.

For frontend development, keep that backend running and use a second terminal:

```bash
cd frontend
npm run dev
```

Open http://127.0.0.1:5173. Vite proxies `/api` to port 8000. `npm run preview` alone does not provide a backend; use the FastAPI server for the built app.

## The four modes

| Mode | Question | Result | Saved routing |
| --- | --- | --- | --- |
| Choice | Which team handles the main request? | Selected team, probabilities, confidence | Unchanged |
| Noul | Does the customer request a refund? | Probability true, with its complement false | Unchanged |
| Score | How much is work blocked? | Ordered impact distribution and weighted score, 0–2 | Unchanged |
| Combined | All three, plus whether impact is stated | Four answers in one request, then Python policy | Applied |

Single modes preview a decision. Combined applies rules: team confidence below 0.8, an `other` team, missing impact evidence (`impact_stated < 0.9`), or impact confidence below 0.8 sends the ticket to Needs review. Otherwise, impact scores at least 1.5 get Urgent priority; other scores get Standard. These are teaching thresholds, not calibrated guarantees. A refund flag records intent and never triggers a payment.

Questions run independently against the same ticket. The impact question cannot read the answer to `impact_stated`; Python combines them afterward. Score is the weighted average of zero-based rubric positions. Confidence measures the returned distribution, not demonstrated accuracy on your customers.

Expand **Inspect the question**, **Python code**, or **Raw response** to explain the request and result. Python examples are generated from the app's question definitions and use a clearly labelled sample ticket.

## Recording sequence

1. Select Amelia's refund ticket. Run Choice. Explain the selected team and distribution.
2. Switch to Noul. Show that changing mode costs no request. Run it to reveal refund probability.
3. Switch to Score. Explain why work continuing normally should receive low impact.
4. Run Combined. Show the saved queue and priority, then filter Billing.
5. Open All tickets and select Marcus's outage. Run Combined and inspect its priority.
6. Select Sofia's vague request. Run Combined and explain why insufficient context needs review.
7. Click Correct to save a human team/priority decision. The original response remains visible; later model runs never replace the correction.
8. Create your own ticket and classify it. Reload to demonstrate persistence.
9. Reset demo restores the original unclassified samples after confirmation. This deletes only this demo's tickets, runs, and corrections.

Actual model answers may vary. Explain surprising results instead of substituting fabricated output. Timing is measured around the SDK request and is not a benchmark comparison.

## Data, recovery, and boundaries

SQLite lives at `instance/desk.sqlite3`, ignored by Git. Set `SUPPORT_DESK_DB` to use another database. Tickets are saved before classification. Failures leave prior results and routing intact and allow a new run. Runs persist in SQLite; the interface shows the latest run for the selected mode. A new failed run shows its error rather than presenting an older success as current.

One run per ticket can be active. Calls have a 30-second timeout with no automatic retry. Abandoned runs expire after 90 seconds; a late response cannot replace newer results. Reset refuses while any unexpired run is active. The interface polls for a run already in progress after reload.

This is a loopback-only recording demo with no login system. Keep it bound to `127.0.0.1`. It sends ticket subject/body to TypeSafe. The API key stays in Python. There is no mailbox connection, refund execution, generated reply, or production deployment configuration.

## Checks

```bash
.venv/bin/python -W error::ResourceWarning -m unittest discover -s tests -v
.venv/bin/pip check
cd frontend
npm run test
npm run build
npx prettier --check src package.json tsconfig.json vite.config.ts index.html
```

See [design](docs/design.md) for acceptance criteria and [verification](docs/verification.md) for recorded test evidence.

## Source map

- `backend/classifier.py`: question definitions, runnable Python examples, Jev call, and routing policy.
- `backend/store.py`: SQLite tickets, run history, concurrency claims, and seed tickets.
- `backend/app.py`: FastAPI endpoints and built frontend hosting.
- `frontend/src/App.tsx`: ticket inbox, mode switch, results, forms, and corrections.
- `frontend/src/style.css`: responsive interface.

References: [TypeSafe primitives](https://docs.typesafe.ai/introduction), [FastAPI](https://fastapi.tiangolo.com/tutorial/first-steps/), [Vite](https://vite.dev/guide/).
