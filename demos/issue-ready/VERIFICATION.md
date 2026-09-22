# Verification

Verified on 2026-09-22.

- Seven unit tests pass: label thresholds, invalid probabilities, invalid inputs,
  changed-issue protection, preserving unrelated labels and repeat runs, preview,
  and API failure before label writes.
- Ruff lint and formatting pass.
- Real Jev call on vague.json: needs-clarification. Yes probabilities: clear
  request 0.36, testable outcome 0.16, unresolved decisions 0.61.
- Real Jev call on clear.json: needs-review. Yes probabilities: clear request
  0.94, testable outcome 0.90, unresolved decisions 0.25. This did not meet the
  teaching cutoff for agent-ready; no threshold was changed to force that label.
- Fresh independent review: Approve, no blocking findings.

GitHub authentication and issue listing worked. The repository had no open
issues, so no live issue labels were changed. Label preservation and replacement
were verified with a mocked GitHub API, not an end-to-end GitHub write. Model
outputs may differ on subsequent runs. No accuracy or calibration claim is made.
