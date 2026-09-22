# Ticket queue verification

Verified on 22 September 2026 with Python 3.14.6 and Node 24.20.0.

## Automated checks

12 backend tests and 5 React integration tests pass. The TypeScript/Vite build, Prettier check, Ruff check, and pip dependency check pass. The independent code reviewer reran the tests, build, and formatting and approved.

| Criterion | Result | Evidence |
| --- | --- | --- |
| AC-1: One request, two Choice questions on creation | Pass | SDK call shape asserted; create endpoint asserts one call; React create test and live browser creation |
| AC-2: Selected labels, probabilities, details | Pass | Queue tests assert 94% department and 78% priority; live distributions inspected |
| AC-3: Field and ticket review below .8 | Pass | Tests distinguish category probability from confidence, check exact .8 and .7999, confident Other, and review filtering |
| AC-4: Failure preserves ticket, retry and concurrent claims | Pass | Failed create returns201 with saved message; retry succeeds in test; concurrent requests rejected; expired completion cannot overwrite newer result; browser invalid-key flow offers retry |
| AC-5: Legacy messages preserved, no automatic read calls | Pass | Migration contract test retains old message and excludes obsolete labels; explicit reclassification works; fresh database and read requests make zero provider calls |
| AC-6: Desktop/mobile/keyboard | Pass | 1440×1050 and 390×844, no horizontal overflow; Enter submits form and toggles review filter; expanded detail and empty review states checked |
| INV-1: Key stays server-side, text remains text | Pass | Config assertion excludes credential, provider failures sanitized, React renders text content |
| INV-2: Raw probability drives threshold | Pass | Tests use low confidence/high probability and high confidence/low probability; unrounded threshold boundary asserted |

## Actual Jev rehearsal

Only synthetic example messages were sent for these checks. These are observations, not accuracy or speed benchmarks.

- GitHub account locked for one employee: IT Support 100%, High 99%, 761 ms.
- Production API outage for all customers: Engineering 100%, Critical 100%, 687 ms.
- Unclear request: Other 91%, Normal 73%, 675 ms. Priority alone was flagged; the ticket appeared in Needs review. Its full distributions were visible in the expanded row.
- Invalid-key instance: newly created ticket retained its message, displayed a safe error, and enabled Retry classification.

The main browser console had no captured errors or warnings. Existing tickets were preserved without showing their earlier taxonomy as current classification. The example picker only fills form fields. The currently running demo uses the real TypeSafe SDK and account key; it does not contain a simulated-response mode.

Screenshots: [desktop queue](evidence/queue-desktop.png), [mobile review queue](evidence/queue-mobile.png). Earlier screenshots in the evidence folder belong to previous versions and are not proof of the current layout.

## Limits

This is a local single-user recording demo, with no authentication or production hosting setup. No model accuracy estimate or threshold calibration is claimed. A vague message can still receive a high probability; the system flags probability below the threshold, not every objectively ambiguous message. Low and Normal are distinguished by the documented priority rubric. There is no automatic operational action after classification.
