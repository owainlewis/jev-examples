# Verification

Verified on 2026-09-22. No personal emails were accessed.

## Real Jev demo

Eight fictional messages were sent to `jev-1.13.0` in eight calls. The API reported
5,091 input tokens. At $0.042 per million input tokens, estimated Jev usage cost
was $0.000213822 (about 0.0214 US cents). Classification and cache work took 5.46
seconds locally. This is one small run, not a throughput or accuracy benchmark.

- Paid video offer: sponsorship, needs attention.
- Consulting enquiry: business enquiry, needs attention.
- Community access request: AI Engineer, needs attention.
- Newsletter: other, no action.
- Completed sponsorship payment: sponsorship, no action.
- Vague collaboration: business enquiry at 65%, action at 70%, needs review.
- Private company workshop: business enquiry, needs attention.
- Generic sales email containing classification instructions: other, no action.

Results were observed, not asserted as guaranteed outputs. The injected text
example is not a general proof of prompt-injection resistance.

A repeat with the same cache made zero API calls and reused all eight results;
new input tokens and estimated new Jev cost were both zero.

## Automated checks

Eleven unit tests cover threshold and probability validation, cache reuse and
account separation, prompt-change invalidation, failure retries and secret-safe
errors, missing usage, empty/oversized messages, duplicate IDs, concurrent runs,
plain/HTML MIME parsing, attachment exclusion, and Gmail pagination/partial flags.
Ruff lint, formatting, and git whitespace checks pass.

Gmail parsing and pagination use fixtures. Live Gmail OAuth, token renewal, and
message fetching were not tested because no Gmail credentials were provided.
The authorization flow and adapter remain unverified end to end. No automation
was scheduled. No mail can be sent, labeled, archived, or deleted by these scripts.
