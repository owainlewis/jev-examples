# Verification

Checked locally on 21 September 2026 with Python 3.14 and the pinned dependencies in `requirements.txt`. The SDK declares Python 3.10+ support; this run did not exercise every supported Python version.

## Acceptance checks

| Criterion | Result | Evidence |
| --- | --- | --- |
| AC1: runnable Noul, Choice, and Score examples with correct result explanations | Pass | All three `examples/` scripts ran against Jev. Refund probability 0.98; selected billing with confidence 1.0; workaround impact 1.0 with confidence 1.0. These are individual observations. |
| AC2: support app saves, classifies, displays answers, persists corrections, filters, and recovers from API failure | Pass | Browser flow plus automated persistence, error/retry, filtering, and concurrent-review tests. |
| AC3: email command validates input, preserves IDs, separates Other from uncertainty, and fails without partial JSON | Pass | Focused tests plus five synthetic live classifications. No mailbox access or changes. |
| AC4: screen-friendly walkthrough and agent instructions match the implementation | Pass | Commands executed, local links checked, official TypeSafe/Codex/Claude documentation checked, independent diff review. Business Inquiry remains provisional. |
| AC5: focused tests and honest measurement evidence | Pass | 18 automated tests, compilation, dependency check, browser checks, and retained live rehearsal report. |

## Automated checks

```bash
.venv/bin/python -W error::ResourceWarning -m unittest discover -s tests -v
.venv/bin/python -m compileall -q examples jev_tutorial src
.venv/bin/python -m pip check
git diff --check
```

All passed. The tests use controlled responses to check application behavior, including an API call completing or failing after a human has already reviewed the ticket. Overlapping retries make only one model call. An interrupted attempt can be retried after its two-minute lease; its late success or failure cannot overwrite the replacement attempt. The overlapping-retry test failed before the fix (HTTP 200 instead of 409) and passed afterward. These tests do not measure model quality.

## Browser checks

Used the Codex in-app browser against the local Flask app with separate test databases:

- Empty inbox and ticket form render.
- Submitted the PDF/CSV ticket through the UI and received a live technical classification, impact 1.0, and no refund intent.
- Changed the team to billing, selected standard priority, and saved using the keyboard. The saved correction appeared alongside the unchanged original technical assessment.
- Filtered the inbox by billing and found the corrected ticket.
- Submitted a vague ticket; it appeared as needing review with a missing-impact explanation.
- Inspected desktop and 390px mobile layout. The mobile document width and scroll width were both 390px, with no horizontal overflow.
- Started an invalid-key instance, submitted a ticket, and saw the saved-ticket failure message and retry control.
- Restarted that instance with the normal key, reloaded the saved ticket, and retried successfully. The ticket and its original submission time survived the restart. See the [support desk capture](evidence/support-desk.png).
- After the retry fix, restarted against the earlier database and confirmed existing tickets survived migration. A controlled synthetic pending record showed the running-state message and no retry control. Lease expiry and stale completions were checked in the automated tests.
- Browser console contained no warnings or errors during these flows. Server request logs showed successful page/asset loads and expected redirects, with no failed UI requests.

The CSS detector ran in degraded regex mode because its optional parser modules were unavailable. It reported no matches; that is not a full accessibility or contrast audit. Visual browser inspection supplied the layout check.

## Live measurements

Ran `python -m jev_tutorial.triage`, the three primitive scripts, the updated single-email example, `python -m jev_tutorial.email_cli data/emails.json`, and `python -m jev_tutorial.evaluate` using synthetic inputs only.

The [saved rehearsal report](evidence/jev-rehearsal-2026-09-21.json) contains all twelve ticket results, timestamp, model version, usage, and timing. Eleven team labels matched expectations. Five tickets passed automatic routing; none of those five had a wrong team label. The auto-renew settings mismatch is retained. This is a teaching set, not an independent benchmark or validation of every returned field.

The email CLI returned the four intended broad categories on the four clear emails and sent the vague collaboration email for review. The live email command was executed from this Codex task. A separate interactive Claude Code session and optional skill auto-discovery were not exercised. Their documented setup follows the official product documentation; demonstrate them before recording that segment.

No comparative LLM benchmark, live mailbox integration, or production deployment was performed. No general speed, accuracy, or savings claim follows from these checks.
