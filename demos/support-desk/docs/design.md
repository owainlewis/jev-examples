# Internal ticket queue

## Outcome

The presenter creates a ticket and sees its Department and Priority, each with its category probability. A single table replaces the previous multi-panel teaching interface. Clicking a request reveals its message and both distributions. The original tutorial examples stay separate.

## Decisions

Department is Choice: HR, Finance, Engineering, IT Support, Other. Engineering owns the company's product; IT Support owns employee tools and access. Priority is Choice: Low, Normal, High, Critical. Both questions run in one request. The highest category probability determines the label. Below 80% flags that field and the whole ticket for review; exactly 80% passes. Other is not automatically uncertain. This uses probabilities, not the separate SDK confidence statistic.

Create saves the ticket first, then calls Jev. Failures return the saved ticket and an actionable retry. There is no type explorer, refund flag, impact score, code panel, correction form, or reset UI. Examples fill the create form; they do not make API calls. New databases start empty. Old tickets remain, but legacy classifications are excluded from the current UI until explicitly reclassified. Historical responses stay stored.

## Acceptance criteria

- AC-1: Creating a ticket makes one request containing exactly two Choice questions; the result is saved and displayed without a second click.
- AC-2: Queue rows show selected Department and Priority with their category probabilities. Opening a row shows original text and complete distributions.
- AC-3: A category probability below .8 flags its field and the ticket. The Needs review filter includes either uncertain field. Exactly .8 and a confident Other do not trigger review.
- AC-4: Failure preserves the ticket, displays the error, and allows retry. Active and expired claims cannot overwrite newer results.
- AC-5: Existing messages survive the taxonomy change. Old labels are not presented as new classifications. Startup and reads do not spend API calls.
- AC-6: The single queue and inline form work on desktop, mobile, and keyboard with clear loading and empty states.
- INV-1: Credentials remain server-side. Ticket text is rendered as text, never HTML.
- INV-2: The numeric threshold compares unrounded probabilities; displayed probabilities are not confidence scores or accuracy claims.

## Checks and limits

API tests prove question shape, threshold boundaries, persistence, legacy-data handling, retries, and concurrency. React tests prove probabilities, review filtering, creation, retries, and stale-poll protection. Browser checks exercise actual Jev responses and both viewport sizes. This is a single-user local demo; model classifications and the threshold need evaluation before any production use.
