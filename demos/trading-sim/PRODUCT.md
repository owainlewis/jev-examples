# Jev trading simulator

A local web demo for a developer recording a Jev tutorial. It consumes public BTC-USD prices, asks Jev for buy/hold/sell decisions, and measures simulated profit after trading costs. It cannot place real orders.

## Platform
Web: Python FastAPI, React, shadcn/ui, SQLite. A self-contained demo separate from the basic Python examples and support app.

## Acceptance criteria
- Live public quotes update the chart; replay is labelled synthetic.
- Jev supplies real probabilities; failures never become fabricated decisions.
- Fills use a quote after the decision and include spread, fees, and slippage.
- Pause/reset invalidate in-flight decisions; stale data prevents execution.
- Cash cannot be borrowed and only one position can be open.
- Desktop and mobile controls work with keyboard focus and visible errors.

## Verification
Unit tests cover the ledger. Integration checks exercise feed and Jev. Browser checks cover start, pause, source change, reset, and narrow layout. Independent review checks the final diff.
