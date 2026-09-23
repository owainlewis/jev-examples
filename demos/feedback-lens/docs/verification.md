# Verification

Verified locally on 2026-09-23 using Python 3.11.11, Node 24.20.0, and the Codex in-app browser. The development server used `127.0.0.1:8017`. Credentials were loaded from an authorized external dotenv file and were not copied into the worktree or printed.

| Criterion | Result | Evidence |
| --- | --- | --- |
| AC-1: one live request, three typed answers | Pass | SDK adapter test asserts one `system_one` call with three questions. Live browser runs returned Choice, Noul, and Score together. Server access logs showed one POST for each submission. |
| AC-2: examples, editor, loading, errors, retry | Pass | Browser checked empty form, example selection, disabled controls while loading, edits clearing stale output, and reload clearing the session. API tests cover validation and failures. A separate local server with no key showed the setup banner and disabled submission while allowing editing. After restarting with a key, Reconnect preserved the draft. A temporary injected provider failure produced a sanitized error and enabled explicit retry. |
| AC-3: local review rule and explanations | Pass | JavaScript tests cover below/equal/above threshold and unrounded comparison. Keyboard Home/End changed the threshold from 80 to 100 to 50 with no additional POST in server logs. The vague example moved between pass and review while the probabilities stayed fixed. UI exposes exact questions and explains Score, Noul, and uncertainty. |
| AC-4: credentials and HTTP boundaries | Pass | Tests check key omission, missing-key behavior, sanitized errors, input bounds, trusted hosts, cross-origin requests, request headers, static file scope, and concurrency. Browser loaded only same-origin static assets and the API; no credential field exists. |
| AC-5: setup, code quality, responsive/browser checks | Pass | Locked dependencies installed successfully. Twelve Python tests and two JavaScript tests passed; Ruff lint/format and Prettier checks passed; module syntax checks passed. Browser checked 1280×900 desktop and 390×844 mobile, keyboard submission and range control, readable results, and zero horizontal overflow at both widths. |

## Live observations

These are observations from real calls, not fixtures or assertions about what future requests must return.

| Input | Winning theme | Actionable yes | Impact | Server elapsed |
| --- | --- | --- | --- | --- |
| A broken export | Reliability, 100.0% | 91.0% | 1.00 | 0.40 s |
| Too little context | Other / unclear, 96.0% | 5.0% | 0.00 | 0.34 s |
| PDF export fails, no workaround, cannot finish report | Reliability, 100.0% | 86.0% | 2.00 | 0.36 s |
| Look past keywords, submitted via Retry after an injected failure | Usability, 100.0% | 96.0% | 0.99 | 0.34 s |

For the vague input, the other theme probabilities were Reliability 1%, Usability 3%, New capability 0%, and Pricing 0%. This is useful evidence that high category probability does not imply actionable feedback.

The desktop and mobile flows had no JavaScript errors or unexpected failed requests. The error exercise intentionally returned one HTTP 502. The injected failure was isolated in a temporary verification script outside the repository; normal application runs always use Jev.

## Commands

Run from `demos/feedback-lens`:

```bash
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv run --locked ruff check backend tests
uv run --locked ruff format --check backend tests
node --test tests/policy.test.mjs
node --check frontend/app.mjs
node --check frontend/policy.mjs
npx --yes prettier@3.8.1 --check 'frontend/*.{html,css,mjs}' 'tests/*.mjs'
git diff --check
```

The app serves source files directly, so there is no frontend build. Tests inject SDK responses and do not call TypeSafe. Live checks used actual credentials separately. The optional Impeccable detector was limited to regex checks because its HTML parser dependencies were unavailable; responsive screenshots and browser checks provided visual evidence. No public hosting, load testing, or screen-reader testing is claimed.
