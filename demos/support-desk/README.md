# Jev ticket queue

A small internal request queue for a tech company. Create a ticket and Jev classifies **Department** and **Priority** in one real API request. Both results show the selected category's probability. Any field below 80% is flagged and the ticket appears in Needs review.

## Run locally

Requires Python 3.11+ and Node 22.12+ (or Node 24). From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your `TYPESAFE_API_KEY` to `.env`. Exported environment variables take precedence. Restart the backend after changing the key.

```bash
cd frontend
npm ci
npm run build
cd ..
uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. For frontend development, keep the backend running and run `npm run dev` inside `frontend`; open port 5173. The Vite dev server proxies `/api` to port 8000.

## The two questions

Both questions use **Choice**, independently against the same ticket.

| Department | Owns |
| --- | --- |
| HR | Benefits, leave, recruiting, people policies, workplace concerns |
| Finance | Invoices, expenses, payments, budgets, payroll payment discrepancies |
| Engineering | The company's own product and production systems |
| IT Support | Employee devices, software, internal tools, passwords, and access |
| Other | Requests clearly outside those departments |

| Priority | Meaning |
| --- | --- |
| Low | Routine request with no stated time pressure or disruption |
| Normal | Needs attention, but work can continue |
| High | An employee is blocked, or an explicit deadline is at risk |
| Critical | Widespread outage, active security incident, or immediate serious business impact |

The largest category probability selects the displayed label. A field below 0.8 gets a Needs review label, and either uncertain field puts the whole ticket in the review queue. The suggested label and its probability stay visible. Exactly 0.8 passes. Other is a real category, not an uncertainty fallback. Jev's separate `confidence` statistic is not used for this rule.

The threshold is a demonstration starting point, not a calibrated accuracy guarantee. The model can be confidently wrong. In particular, a vague or exaggerated message is not guaranteed to produce a low probability; show its actual response rather than inventing a result.

## Record the demo

1. Click New ticket and select the HR example. Create it and inspect its department and priority.
2. Create the GitHub access example. Explain why employee access belongs to IT Support, even though GitHub is used by engineers.
3. Create the production outage example and compare High with Critical.
4. Try an unclear message. If either field is below 80%, show the Needs review queue.
5. Click a request to inspect the original message and both probability distributions.

The example picker fills the form only. Nothing calls the API until Create ticket. Each created ticket calls Jev once; a failed classification preserves its message and offers Retry classification. There is no type explorer, code panel, manual correction workflow, or automatic business action.

## Data and migration

SQLite lives at `instance/desk.sqlite3`, ignored by Git. `SUPPORT_DESK_DB` selects another file. Fresh databases start with an empty queue. Older demo tickets remain saved; old team/refund/impact results are not shown as if they used the new taxonomy. Open an old ticket and choose Classify ticket to apply the new questions. Historical raw runs remain in SQLite.

One request per ticket can be active. SDK requests time out after 30 seconds without automatic retry. Abandoned run claims expire after 90 seconds, and late responses cannot overwrite newer results. Reloading during an active request starts polling for completion.

This is a local recording demo, not a hosted multi-user service. Keep it bound to loopback. Ticket subject/body are sent to TypeSafe; the key remains in Python. The app uses `typesafe-sdk` against `https://api.typesafe.ai`, with no simulated results. Check your TypeSafe console for balance and usage.

## Verify

```bash
.venv/bin/python -W error::ResourceWarning -m unittest discover -s tests -v
cd frontend
npm run test
npm run build
npm run format:check
```

See [design](docs/design.md) and [verification](docs/verification.md). Implementation: `backend/classifier.py` defines the questions and threshold, `backend/app.py` owns HTTP requests, `backend/store.py` owns persistence, and `frontend/src/App.tsx` owns the queue.
