# Task: Feedback Lens

Build one complete local product-feedback workbench that demonstrates Jev's Choice, Noul, and Score together.

## Acceptance criteria and checks

- **AC-1:** One explicit submission makes one real Jev request and displays theme (Choice), actionable request (Noul), and workflow impact (Score), including distributions. Check the SDK adapter with unit tests and a live browser request.
- **AC-2:** Fictional examples, editable input, empty, loading, error, and retry states work. Check invalid input and provider failures in API tests; exercise the UI in a real browser.
- **AC-3:** A local review threshold uses the winning theme probability. Adjusting it never calls Jev. Explain Noul, the fractional Score, and the limits of probabilities. Check threshold boundaries with JavaScript tests and browser interaction.
- **AC-4:** API credentials remain server-side, provider errors are sanitized, and cross-origin paid requests are rejected. Check configuration, static file scope, input limits, and request guards in API tests.
- **AC-5:** Provide exact setup and usage instructions. Verify Python tests and formatting, JavaScript syntax and tests, keyboard interaction, and desktop/mobile layouts. There is no frontend compilation step.

## Scope

Reuse this managed worktree. Inherit the neutral support-desk visual system, with an input pane and an inspection pane. No deployment, merge, database, account system, generated explanations, or external business actions. Review the finished diff independently, then commit, push, and open a PR.
