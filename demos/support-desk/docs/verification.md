# Verification

Verified on 22 September 2026. Python 3.14.6, Node 24.20.0. This is a local recording app, not a production help desk.

## Automated proof

- 15 backend tests pass: `.venv/bin/python -W error::ResourceWarning -m unittest discover -s tests -v`.
- 3 React integration tests pass: `npm run test`.
- TypeScript and Vite production build pass: `npm run build`.
- `ruff check backend tests`, Python compilation, `pip check`, and `npm run format:check` pass.
- After dependency patches, npm reported zero known vulnerabilities.

| Criterion | Result | Evidence |
| --- | --- | --- |
| AC-1: Explicit requests and correct question sets | Pass | SDK call assertions for all four modes; React test changes modes without a mutation request; four live modes exercised in browser |
| AC-2: Typed displays and matching code | Pass | Live Choice distribution, Noul true/false, Score 0–2 distribution; generated code executed up to provider call and compared with backend definitions; code and raw panels opened in browser |
| AC-3: Combined-only routing and persistence | Pass | Preview routing remains null in tests; Combined persisted through fresh Store; live browser reload retains queue and priority |
| AC-4: Create, presets, filters, correction, reset | Pass | Live custom account ticket; Billing filter; vague ticket corrected; reset cancellation preserves data, confirmed reset restores four unclassified presets; empty Billing queue shown |
| AC-5: Failures, retries, concurrency | Pass | Sanitized failure and preserved history tests; overlapping run/reset blocked; expired completion rejected; reset races reproduced and regression tested; React deferred-response tests preserve correction/reset |
| AC-6: Desktop, mobile, keyboard and states | Pass | Browser at 1440×1050 and 390×844; no horizontal overflow; Enter toggles Noul and submits ticket; loading, empty and provider failure seen; screenshot review disposition ship |
| INV-1: Key remains server-side | Pass | Config test asserts key absent; request body only contains ticket subject/body and questions; provider exceptions sanitized |
| INV-2: Previews preserve routing; human wins | Pass | API tests and live correction; original response remains separate from manual override |

## Live observations

The four preset tickets are invented. No real customer data was used.

- Refund: Choice selected Billing with probability 1.0. Noul returned 0.98 for refund intent. Score returned 0.0 with all mass at the first rubric position. Single-type requests took approximately 607–691 ms in this rehearsal, not a general speed claim.
- First Combined rehearsal revealed an overly strict impact-evidence question. It asked for both work status and workaround information, returning 0.87 and requiring review on an otherwise clear ticket. The question was changed to ask whether impact is explicitly described as normal work, a workaround, or blocked work. Thresholds were unchanged.
- Updated Combined: refund routed to Billing / Standard; impact evidence was 0.97.
- Outage: Combined routed to Technical / Urgent.
- Vague request: Combined required review because impact evidence was 0.06. A human correction to Technical / Standard was saved separately.
- Custom account-change request: created through the UI, routed to Account / Standard, then reloaded successfully.
- Separate local instance with an invalid test key: safe actionable error, ticket retained, Run classification re-enabled. No raw credential or provider error was displayed.

The main browser console had no captured warnings or errors. API/static requests succeeded during normal flows. The deliberately invalid-key request returned the expected 502. The initial missing favicon was corrected by adding the app icon.

## Review and limitations

Independent code review found reset transaction gaps and stale polling responses. Both were fixed; the reviewer reran all 18 tests and approved. Independent screenshot review returned **ship** for the supplied desktop and mobile evidence.

Screenshots: [desktop](evidence/desktop.png), [mobile inbox](evidence/mobile.png), [mobile result](evidence/mobile-result.png). Captures show real rehearsal state before resetting the demo. Viewport captures were used because this browser's full-page stitching produced a malformed image.

Only local use was tested. The small synthetic sample does not measure model accuracy, calibrate the thresholds, or establish a latency benchmark. No authentication, multi-user hosting, mailbox integration, or refund execution is included.
