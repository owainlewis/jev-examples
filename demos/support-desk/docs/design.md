# Support desk demo

## 1. Outcome and scope

Build the agreed three-panel support inbox for screen recording, separate from the tutorial modules. React presents the same saved ticket through Choice, Noul, Score, and Combined. FastAPI calls Jev and SQLite persists tickets and runs. This folder has its own dependencies and can be copied out of this repository. It imports nothing from the tutorial package.

## 2. Behaviour and decisions

The presenter selects a preset or creates a ticket, selects a mode, reads the question, and clicks Run classification. Changing mode never calls the API. Single types are previews; Combined asks all questions in one request and applies Python routing policy. Missing impact or uncertainty sends the ticket to Needs review. A refund flag describes intent, never authorises payment. Human corrections remain separate from model output and survive later runs.

The existing warm white, ink, and green visual system carries into the agreed queue/list/detail composition. A horizontal segmented mode control and visible question make the teaching sequence clear. Results use labelled bars, a binary meter, and an ordered impact rubric. Code and raw response are expandable. Mobile stacks the panels. No comp selection is needed because the user has approved this composition and asked to build it.

## 3. Data and lifecycle

Tickets have UUIDs, immutable subject/body, creation time, optional routing and manual correction. Runs have UUIDs, ticket ID, mode, running/succeeded/failed state, timestamp, exact response and elapsed time. Each ticket permits one live request across modes, claimed atomically in SQLite. A 90-second lease recovers abandoned runs; the SDK has a 30-second timeout without automatic retry. Late results cannot overwrite a newer claim. Reset removes only this demo's data and restores synthetic presets, following explicit UI confirmation; it refuses while runs are active.

## 4. Local boundary

Bind to loopback. Keep the API key in the backend environment; never put it in frontend code. API mutations require JSON and a custom request header, with no cross-origin allowance. Trusted-host validation rejects unknown hosts. Ticket content is plain text. Provider errors are reduced to safe actionable messages. This local demo has no account system or hosted deployment support.

## 5. Acceptance criteria and invariants

- AC-1: Four modes make requests only on an explicit click; each includes exactly the declared questions.
- AC-2: Choice displays its distribution; Noul displays true/false probability; Score displays its ordered distribution and weighted score. Code is generated from the same question definitions used by the backend.
- AC-3: Only Combined applies automatic routing, with review on unclear impact or uncertain answers. Saved routing survives restart.
- AC-4: Create, presets, queue filters, manual corrections, and reset work. Corrections remain distinct from original results.
- AC-5: Failure preserves the ticket and previous successful runs; retry is possible. Concurrent and stale requests cannot overwrite later decisions.
- AC-6: Desktop, mobile, keyboard controls, loading, empty, and error states are usable. Real API results are clearly distinguished from empty states.
- INV-1: API keys never enter browser responses or committed files.
- INV-2: Preview runs never mutate routing. Human corrections always win over model routing.

## 6. Proof

Focused API tests cover AC-1 through AC-5 and INV-1/2 with deterministic provider responses, including concurrency and expiration. Frontend type checking and production build check contracts. Browser checks cover AC-6 and full create, mode-switch, classify, correction, and reset flows with actual Jev requests where credentials are available. Record limitations in verification.md. Review the complete demo diff independently before delivery.

## 7. Tradeoffs and exclusions

SQLite and synchronous provider calls keep setup small. This is for local recording, not multiple authenticated agents or large queues. No real mailbox, model router, refund execution, generated replies, or changes to the existing tutorial app.
