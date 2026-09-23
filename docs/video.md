# Jev for AI developers: real use cases

## Introduction

Jev is an AI model from TypeSafe AI. It takes text and returns structured output. You provide a question and define the kind of answer you need: a yes/no probability, a category, or a score.

For example, you can ask whether a customer is unable to access their workspace, which department should receive a ticket, or how much a problem blocks someone's work. Your code reads the result and decides what to do next.

This tutorial explains the three question types, then shows them in Python, a support ticket app, a Codex model router, and an email triage skill. The code and setup instructions are included in this repository.

## How Jev works

### Send a ticket, get a category

Suppose a customer sends this ticket:

> I cannot sign in to my workspace. Every attempt shows a server error, so I cannot access my projects.

We ask: **Which team should handle this ticket?** We define four possible answers:

| Answer | What it covers |
| --- | --- |
| Billing | Payments, invoices, and subscription charges |
| Technical | Errors, broken features, and help using the product |
| Product | Feature requests and product feedback |
| Other | Requests outside these categories |

Jev returns a selected answer and a probability for every option. Here is an illustrative result, not a recorded API response:

| Answer | Probability |
| --- | ---: |
| Billing | 2% |
| Technical | 94% |
| Product | 1% |
| Other | 3% |

The selected answer is Technical. Our code can route the ticket automatically if its selected probability is at least 80%. Below that threshold, it can send the ticket for review.

```mermaid
flowchart LR
    T[Customer ticket] --> J[Jev: choose a team]
    J --> P{Selected probability at least 80%?}
    P -->|Yes| A[Assign to selected team]
    P -->|No| R[Send for review]
```

Jev supplies the answer and probabilities. Our application supplies the threshold, saves the ticket, and assigns the team. Classifying an access problem does not change the customer's account permissions.

### Classify text without training your own model

Classification means assigning an input to a category. It is an established machine learning task. With Jev, you describe the categories in the request instead of training a separate model for each set of labels.

The same model can classify support tickets by team or emails by business purpose. You still need clear criteria and examples with known answers to test it. TypeSafe documents that customization happens through the supplied state, instructions, and criteria, rather than customer-specific fine-tuning. See [model customization](https://docs.typesafe.ai/models).

Restricting the allowed answers controls their format. It does not prove that the selected answer is correct or that repeated calls will always agree.

### What goes into the request?

The API uses three terms:

| Term | Meaning | In this example |
| --- | --- | --- |
| State | The text or structured text data to evaluate | The ticket title and message |
| Instructions | The question to answer | Which team should handle this ticket? |
| Criteria | Descriptions of the options or levels | Technical covers errors, broken features, and help using the product |

A request also specifies the model and a name for each question so your code can find its answer. Noul questions do not need a list of criteria.

Supply the information needed to answer the question. A ticket that says "It still doesn't work" may need earlier messages or reproduction steps. Jev only evaluates the state you send; it does not fetch those details for you. See the [TypeSafe introduction](https://docs.typesafe.ai/introduction).

### Choose the answer type

| Type | Question | Returned value |
| --- | --- | --- |
| Noul | Is the customer unable to access their workspace? | A yes probability, such as `0.92` |
| Choice | Which team should handle this ticket? | One category, plus probabilities for every option |
| Score | How much does the issue block work? | A numeric score, plus probabilities for each defined level |

**Noul returns a number, not a Boolean.** An illustrative value of `0.92` means an estimated 92% probability of yes. Your code could accept values at least 0.9, reject values at most 0.1, and review everything between. These cutoffs are your rules. See [Noul](https://docs.typesafe.ai/primitives/noul).

**Choice selects one option.** For the Technical example, code reads the selected label and then looks up that label's probability:

```python
answer = response.choices["department"]
department = answer.choice
probability = answer.probabilities[department]
```

`department` is the question name chosen for this example. Each category needs a clear description. "Other" means the request falls outside the named categories; it does not mean the model is unsure. See [Choice](https://docs.typesafe.ai/primitives/choice).

**Score uses an ordered scale.** For work impact, we can define:

| Level | Description |
| --- | --- |
| 0 | Work can continue without a workaround |
| 1 | Work can continue with a workaround |
| 2 | Work is blocked and there is no workaround |

With illustrative probabilities of 10%, 60%, and 30%, the score is:

```text
(0 × 0.10) + (1 × 0.60) + (2 × 0.30) = 1.2
```

This is a weighted average of the level numbers. It is not a percentage of users affected. A score of 1 could mean all probability is on level 1, or half is on level 0 and half on level 2. Inspect the probabilities alongside the score. See [Score](https://docs.typesafe.ai/primitives/score).

Use Choice when you need one named category. Use Score when a position on a defined scale is useful, for example when ranking reports by work impact.

### Ask one thing per question

"What should we do with this ticket?" mixes several decisions. Split it into questions your code can use:

- Which department should handle it?
- What priority does it deserve?
- Does it contain enough information to investigate?

You can mix question types in one request. Each question reads the same state independently. It does not see the other questions' answers.

```mermaid
flowchart LR
    T[Ticket text] --> D[Choice: department]
    T --> P[Choice: priority]
    T --> I[Noul: enough information?]
    D --> C[Python checks results]
    P --> C
    I --> C
    C --> A[Assign, review, or request details]
```

If a later question needs an earlier answer, make another request with that answer included in the state. TypeSafe recommends asking specific questions and combining their results in code. See [the introduction](https://docs.typesafe.ai/introduction).

Write criteria that separate the answers. In a tech company, IT Support might handle employee devices and access, while Engineering handles bugs in the company's product. An engineer asking for GitHub access should go to IT Support. The word "engineer" alone should not determine the department.

### Use probabilities to decide when to review

A label tells us where a ticket might belong. Its probability helps us decide whether to assign it automatically.

Our demo uses an 80% selected-probability threshold. That is a starting setting, not a measured guarantee. Raising it generally sends more tickets for review. Test whether the tickets you still accept automatically are classified accurately enough.

Choice and Score also return `confidence`. This is a statistic derived from how the probabilities are distributed. It is a separate value from the selected option's probability. Neither value is a statistical confidence interval. Our demos use the selected probability for their review rules. See [confidence](https://docs.typesafe.ai/confidence).

TypeSafe calls its training approach Reinforcement Learning for Calibrated Decisions, or RLCD. Calibration means that, across comparable predictions, answers assigned about 80% probability should be correct about 80% of the time. You need many labeled examples to check that. One confident answer can still be wrong. See the [TypeSafe AI primer](https://docs.typesafe.ai/introduction/machine-learning-primer).

### When should you use Jev?

| Need | Approach to consider |
| --- | --- |
| Check whether an invoice is past its due date | Ordinary code comparing dates |
| Decide whether an email disputes an invoice | Jev interpreting the message against defined criteria |
| Investigate the dispute and draft a reply | A language model with the necessary information and tools |

A general-purpose language model can also classify text and return structured output. Jev provides an API built around these question types and their probabilities. Compare accuracy, response time, and total cost on the same examples before choosing it.

TypeSafe calls Jev a System One model, borrowing the name for fast thinking from *Thinking, Fast and Slow*. A reasoning model can do the longer investigation after Jev routes the request. This describes their roles in the workflow; it does not mean they think like people.

Jev does not write replies, generate code, or explain its reasoning. Its current API accepts text and structured text data, not images, audio, or video. A browser integration would need to supply extracted text or element descriptions rather than a screenshot. Your application still needs permissions, business rules, and handling for failed API calls. See [System One](https://docs.typesafe.ai/concepts/system-one).

## Demo: Python question types

Three short files show real API calls using invented tickets:

| Example | What it demonstrates |
| --- | --- |
| [01-noul.py](../src/01-noul.py) | Detect blocked workspace access and use its probability to choose the next step |
| [02-choice.py](../src/02-choice.py) | Select billing, technical, product, or other; review results below 80% |
| [03-score.py](../src/03-score.py) | Score work impact using normal work, a workaround, and blocked work as levels |

The [README](../README.md#run-the-python-examples) covers uv setup and the TypeSafe API key. These examples call the hosted API.

## Demo: support ticket app

The [support app](../demos/support-desk/README.md) uses Python, React, and SQLite. Creating a ticket automatically asks two Choice questions: department and priority.

Departments are HR, Finance, Engineering, IT Support, and Other. Priorities are Low, Normal, High, and Critical. The queue shows both labels and their selected probabilities. If either probability is below 80%, the ticket needs review.

Compare an employee who cannot access GitHub with a production outage affecting customers. The app saves tickets before classification, so an API failure leaves the ticket available for retry.

## Demo: Codex model router

The [Codex router skill](../demos/codex-router/README.md) uses Jev to classify a task as routine, standard, or complex. Python maps the category to a configured model and reasoning level. Codex opens a new task with that model and a complete brief.

The demo asks for a read-only explanation of the Choice example. It shows the classification probability, selected model, and new task. Low probability or an API failure selects the configured complex route.

This selects from a model mapping you control; it does not prove which model is cheapest or will succeed. Creating the new task requires Codex desktop tools. The Python classifier also runs in a terminal.

## Demo: email triage in Codex

The [email triage skill](../demos/email-triage/README.md) runs a Python script against a fictional inbox. It makes real Jev calls without accessing personal emails. Jev selects Sponsorship, Business enquiry, AI Engineer community, or Other. A separate Noul question asks whether the message requires a reply, decision, or task.

The distinction matters even when emails contain the same words. These are shortened versions of three messages from the demo, with the results observed in our test:

| Message | Category | Action |
| --- | --- | --- |
| "Can you send your rates for a sponsored video?" | Sponsorship | Needs attention |
| "The sponsorship payment is complete; nothing else needed." | Sponsorship | No action |
| "Hire you to train our engineers, not sponsor a video." | Business enquiry | Needs attention |

A vague collaboration email received 65% for Business enquiry and 70% for action needed. The script flagged it for review. These are results from one run, not guaranteed outputs or an accuracy benchmark.

Python controls fetching, thresholds, caching, and reporting. Jev makes the classifications. Codex runs the script and presents the report. The workflow is defined in code; the classifications remain model predictions.

```mermaid
flowchart LR
    E[Fictional emails] --> P[Python loads messages]
    P --> J[Jev: category and action needed]
    J --> R[Python saves results and counts tokens]
    R --> C[Codex presents the report]
```

### What did the classification cost?

Our eight-email demo used **5,091 input tokens** and took **5.46 seconds** for classification and cache work. At the published price of **$0.042 per million input tokens**, its estimated Jev cost was:

```text
5,091 / 1,000,000 × $0.042 = $0.000213822
```

That is about **0.0214 US cents**. Output tokens are free at this price. This estimate excludes Codex's report generation and any other services. The report includes the price and its verification date so it can be checked when pricing changes. See [TypeSafe pricing](https://docs.typesafe.ai/models) and our [recorded test results](../demos/email-triage/VERIFICATION.md).

For comparison, assuming exactly 10,000 total input tokens per request:

| Requests | Estimated Jev cost |
| ---: | ---: |
| 1 | $0.00042 |
| 1,000 | $0.42 |
| 10,000 | $4.20 |
| 100,000 | $42.00 |

These are calculations at the same price, not measured workloads. Questions and criteria count toward input usage too.

Repeating our demo with the same cache reused all eight classifications with **zero new API calls**. The saved results are still available, but they add no new Jev usage. Failed calls or missing usage make the full cost unknown; the script reports that rather than calling it free.

## Summary

To try Jev in your own application, choose one question and describe its possible answers. Collect examples with known results, including ambiguous and incomplete inputs.

Measure incorrect automatic decisions, how often review is needed, response time, and cost. If you change the criteria or threshold, check the result on separate examples. Those measurements tell you whether Jev is useful for your application.
