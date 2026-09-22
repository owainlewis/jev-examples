# Recording the Jev tutorial

The main reading view is [tutorial.md](tutorial.md). Keep this file off screen; it contains production notes and the reasoning behind the lesson.

## Promise and audience

For developers comfortable with basic Python: understand Jev's three question types, build a support desk that uses them, and reuse classification in an agent-driven email routine.

Working title: **Build with Jev: Python, a Support App, and Codex**.

Alternative: **Jev in Python: From Your First Decision to a Working App**.

The opening should show a result before explaining the company. Create an export ticket and point to its team, impact, and refund assessment. Promise to explain those three values, wire them into Python, and use the same approach for email.

## Suggested screen sequence

| Approximate time | Screen | Teaching beat |
| --- | --- | --- |
| 0:00–0:45 | Finished support app | One ticket becomes several usable decisions |
| 0:45–2:30 | Tutorial introduction and request diagram | State, questions, typed answers |
| 2:30–5:00 | `examples/01-noul.py` | Probability of yes; three paths in code |
| 5:00–8:00 | `examples/02-choice.py` | Categories, criteria, confidence |
| 8:00–11:00 | `examples/03-score.py` | Ordered rubric and fractional scores |
| 11:00–13:30 | `classifier.py` and combined output | Independent questions; policy stays in code |
| 13:30–18:00 | Browser and `app.py` | Submit, inspect, correct, filter, recover from failure |
| 18:00–22:00 | Email JSON, category config, Codex | The agent actually runs the classifier |
| 22:00–23:00 | Claude Code | Briefly repeat the same command-based workflow |
| 23:00–27:00 | Evaluation output and one wrong answer | Measure quality and cost; explain limits |

These are planning estimates, not timestamps from an edited recording. If it runs long, put optional skill installation and secondary examples in the repository. Keep the three types and the failure case in the video.

## The lesson the first rehearsal exposed

The twelve-ticket run on 21 September 2026 matched 11 expected team labels. Five tickets passed the application's automatic-routing policy; none of those five had the wrong team. The remaining seven went to review. The full synthetic results are saved in [the rehearsal report](evidence/jev-rehearsal-2026-09-21.json).

The auto-renew settings example returned **billing**, while our written policy and expected label say **technical**. It was sent for review. Use this result: read the ticket, read the criteria, show the actual distribution, and explain the policy boundary. Do not edit the expected answer after seeing the model output just to improve the score.

These are observed results on a tiny teaching set. Zero wrong automatic routes among five cases does not prove the system is safe to automate. Re-run before filming, keep changed results, and label every number with the dataset and conditions.

Measured median request time was 274.2 ms; p95 was 796.7 ms. Calls were sequential with one reused client, no warm-up, and retries disabled. The location of the client and network conditions were not controlled. The run used 6,754 input tokens, giving an estimated direct input cost of $0.00028367 at the published rate. This excludes agent orchestration, hosting, and any failed-call costs.

The five sample emails returned AI Engineer, Business Inquiry, Sponsorship, Other, and Other in order. The vague collaboration email had confidence 0.55 and required review. Those were observed outputs, not a validated email benchmark.

## What the two competitor transcripts teach us

The first supplied transcript has a clear SDK walkthrough and a familiar support example. Its current [repository](https://github.com/daveebbelaar/ai-cookbook/tree/main/models/jev) goes beyond the transcript with failure examples and workflows. Our distinction should be a connected build and visible evaluation, not a claim that it never covers fallbacks.

The second supplied transcript connects Jev to coding agents and shows several applications. Borrow the useful connection between classification and agent workflows. Keep our demonstration reproducible: one Python command, real returned JSON, the agent's summary. Avoid switching between games, PR review, browser control, and model routing in the same lesson.

The pasted transcripts were used as editorial context, not copied as narration. No URL or code repository was supplied for the second video, so its demonstrations and performance claims were not independently verified.

## Claims to handle precisely

- A schema-valid answer can be wrong. Do not say “no hallucinations” as a promise of correct decisions.
- A confidence value summarizes a distribution. It does not prove a per-email success rate.
- Score levels are ordered descriptions. Noul is probability of yes, not severity.
- One request can contain independent questions. A dependent question needs the earlier result in its state.
- Classification existed before Jev. Explain the interface and measured application behavior without declaring that all earlier classification systems needed task-specific retraining.
- Avoid unsupported forecasts about other labs shipping a competing model within a few months.
- Business Inquiry remains provisional. Do not present its boundary as Owain's final policy.
- The email segment uses synthetic local JSON. No live mailbox connector, scheduled routine, or label writes are included.
- Codex/Claude Code keep their own model. Jev is called by the Python tool.

## Before recording

1. Run the README setup and each main command. Keep the key and real emails off screen.
2. Use a fresh database for the recording: `JEV_TICKET_DB=instance/recording.sqlite3 uv run python -m jev_tutorial.app`. Use a new filename if it already contains rehearsal tickets.
3. Open the walkthrough, three examples, classifier, app, category config, and synthetic emails. Increase editor font size. Keep terminal output beside the relevant code.
4. Rehearse the successful ticket and the vague ticket. Explain unexpected outputs rather than hunting for a perfect take.
5. Use the documented invalid-key launch to demonstrate failure. Restart normally before the next live call.
6. Open the repository in the coding agent with access to its Python environment. Verify that the agent executes the command. Skill installation is optional.
7. Run the evaluation and retain its JSON. Show disagreements. Avoid general speed rankings based on a dozen calls.

## Sources checked on 21 September 2026

| Source | What it supports |
| --- | --- |
| [TypeSafe introduction](https://docs.typesafe.ai/introduction) | State, questions, structured results |
| [Noul](https://docs.typesafe.ai/primitives/noul) | Yes/no probability |
| [Choice](https://docs.typesafe.ai/primitives/choice) | Named options and results |
| [Score](https://docs.typesafe.ai/primitives/score) | Ordered levels and weighted scores |
| [Confidence](https://docs.typesafe.ai/confidence) | Distribution-derived certainty |
| [Models](https://docs.typesafe.ai/models) | Version, text input, direct API pricing |
| [Python SDK](https://docs.typesafe.ai/sdk/python) | Client and response interface |
| [Jev 1.13 limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13) | Arithmetic, dates, indirection, adversarial inputs |
| [TypeSafe launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev) | Vendor account of RLCD and parallel outputs |
| [Codex skills](https://developers.openai.com/codex/skills/) | Repository skill discovery |
| [Claude Code skills](https://code.claude.com/docs/en/skills) | Project skill location and invocation |

Prefer these primary sources over unofficial sites with similar Jev/TypeSafe names. Refresh price and model-version claims before publishing.
