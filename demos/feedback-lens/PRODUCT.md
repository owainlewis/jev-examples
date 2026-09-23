# Feedback Lens

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Developers learning Jev through a local, working product-feedback demo. The user delegated the use case and interface choices.

## Product Purpose

Make Jev's three answer types visible on the same input. A developer can submit feedback, understand each probability distribution, and see how a review threshold changes an application decision without changing the model's answer.

## Stack

FastAPI and the repository's pinned TypeSafe SDK, with plain HTML, CSS, and JavaScript. One local server, no frontend build or database required.

## Capabilities and Constraints

One explicit submission calls Jev once with Choice, Noul, and Score questions. The app displays live results only. Fictional examples fill the input without calling the API. The key stays on the server. Feedback is sent to TypeSafe and is not persisted by this app. Reload clears results. This is a loopback-only demo, not a hosted service.

## Product Principles

- Explain the relationship between input, model output, and application policy.
- Preserve uncertainty and show the underlying probabilities.
- Never imply that a probability is a measured accuracy guarantee.
- Keep local setup small and independent of the existing demos.
