# Five more ways to use Jev in Python

Use Jev when your program needs a judgment about text. Give it a narrow question and let your code handle the result. These are optional examples after the [main walkthrough](tutorial.md), which covers the three types, the support app, and the Codex/Claude Code email workflow.

Each example below is a separate script. Complete the README setup. The runnable files in `src/` load `.env`; the standalone code blocks below use an exported `TYPESAFE_API_KEY`. To run a block, save it to a `.py` file and run `uv run python your_file.py`.

The examples call the hosted model and print suggestions. They do not update another service. All input data is invented. Thresholds are teaching examples that need testing on your own data.

## 1. Put blocked customers at the front of a support queue

Ask how much the reported problem prevents the customer from working. This is different from measuring how angry their message sounds.

Use `Score` with descriptions ordered from least to most severe. The first level is 0, the second is 1, and the third is 2. Results can fall between levels. See [Score](https://docs.typesafe.ai/primitives/score).

```python
from typesafe_sdk import Score, TypeSafeClient

with TypeSafeClient(model="jev-1.13.0", timeout=30.0) as client:
    response = client.system_one(
        state={
            "message": (
                "The PDF download is broken. I can still download a CSV "
                "and use that for today's report."
            ),
        },
        questions={
            "impact": Score(
                instructions="How much does the reported problem block the customer's work?",
                criteria=[
                    "The customer can complete their work without a workaround",
                    "The customer can complete their work using a workaround",
                    "The customer cannot complete their work and has no workaround",
                ],
            ),
        },
    )

impact = response.scores["impact"]
print("Impact score:", impact.score)
print("Confidence:", impact.confidence)
if impact.confidence < 0.8:
    print("Queue: manual triage")
elif impact.score >= 1.5:
    print("Queue: blocked customers")
else:
    print("Queue: standard support")
```

The sample describes a workaround, so level 1 is the intended result. A score is a position on your scale, not a count of affected customers or a promised response time.

## 2. Sort incoming documents

A shared inbox may receive invoices, meeting notes, and product specifications. Classify their text before choosing where to file them.

Jev 1.13 accepts text, not raw PDFs or images. Extract document text first. A scanned document needs text recognition before classification. See [supported inputs](https://docs.typesafe.ai/models).

```python
from typesafe_sdk import Choice, TypeSafeClient

document_text = """
Project meeting, 12 September.
Decision: keep the existing checkout flow for the next release.
Action: Sam will test the mobile payment screen by Friday.
"""

with TypeSafeClient(model="jev-1.13.0", timeout=30.0) as client:
    response = client.system_one(
        state={"text": document_text},
        questions={
            "document_type": Choice(
                instructions="What kind of document is this text?",
                criteria={
                    "invoice": "A request for payment with charges or an amount due",
                    "meeting_notes": "A record of meeting discussion, decisions, or actions",
                    "specification": "Requirements or a proposed design for a product",
                    "other": "Another document type, mixed content, or insufficient text",
                },
            ),
        },
    )

answer = response.choices["document_type"]
folder = answer.choice if answer.confidence >= 0.8 else "manual_review"
if folder == "other":
    folder = "manual_review"
print("Suggested folder:", folder)
```

The intended folder is `meeting_notes`. Add your own document types and examples before connecting this to a filing system.

## 3. Give product feedback more than one tag

One message can contain both a bug report and a feature request. A single `Choice` selects only one category. Separate `Noul` questions let several tags apply.

`noul` is the estimated probability that the answer is yes. It is not a Python boolean and has no separate `confidence` field. See [Noul](https://docs.typesafe.ai/primitives/noul).

```python
from typesafe_sdk import Noul, TypeSafeClient

with TypeSafeClient(model="jev-1.13.0", timeout=30.0) as client:
    response = client.system_one(
        state={
            "feedback": (
                "The export button fails on my phone. "
                "I'd also like a way to schedule weekly exports."
            ),
        },
        questions={
            "bug": Noul(instructions="Does the feedback report existing behavior that fails?"),
            "feature_request": Noul(
                instructions="Does the feedback request a new product capability?"
            ),
            "praise": Noul(instructions="Does the feedback express satisfaction with the product?"),
        },
    )

tags = []
review = []
for name, answer in response.nouls.items():
    if answer.noul >= 0.85:
        tags.append(name)
    elif answer.noul > 0.15:
        review.append(name)

print("Suggested tags:", tags)
print("Tags needing review:", review)
```

The intended tags are `bug` and `feature_request`. Each question is independent, so the probabilities across questions do not need to add up to 1.

## 4. Filter search results before answering a question

A search engine can return passages that mention the right topic but do not answer the user's question. Ask Jev whether each passage contains useful answer material.

Your search system must supply the passages. Jev does not retrieve them in this example. TypeSafe also documents [classifying retrieved passages](https://docs.typesafe.ai/cookbooks/classifying_rag_passages).

```python
from typesafe_sdk import Noul, TypeSafeClient

question = "How can I export my workspace data?"
passages = {
    "export_help": "Open Settings, select Data, then choose Export workspace.",
    "profile_help": "Open your profile menu to update your display name.",
    "export_news": "Workspace export was announced in our September newsletter.",
}

useful = []
review = []
with TypeSafeClient(model="jev-1.13.0", timeout=30.0) as client:
    for passage_id, text in passages.items():
        response = client.system_one(
            state={"user_question": question, "passage": text},
            questions={
                "useful": Noul(
                    instructions=(
                        "Does the passage contain information that answers the "
                        "user_question, rather than merely mentioning its topic?"
                    ),
                ),
            },
        )
        probability = response.nouls["useful"].noul
        if probability >= 0.85:
            useful.append(passage_id)
        elif probability > 0.15:
            review.append(passage_id)

print("Passages to consider:", useful)
print("Passages needing review:", review)
```

`export_help` is the intended useful passage. Relevance does not prove that a passage is true or current. Keep its source link when passing it to an answering system. This simple loop makes one request per passage.

## 5. Suggest duplicate bug reports

Two reports may describe the same symptom in different words. Compare a new report with a possible duplicate and suggest a link for a maintainer to check.

Use search to find candidates first. Comparing every report with every other report becomes expensive as the collection grows.

```python
from typesafe_sdk import Choice, TypeSafeClient

with TypeSafeClient(model="jev-1.13.0", timeout=30.0) as client:
    response = client.system_one(
        state={
            "new_report": {
                "id": 81,
                "text": "Safari shows a blank preview when I upload a PNG avatar.",
            },
            "existing_report": {
                "id": 29,
                "text": "PNG profile photos have an empty preview in Safari.",
            },
        },
        questions={
            "relationship": Choice(
                instructions=(
                    "Compare the reported symptom, affected feature, and conditions "
                    "of the two reports. Do not assume a shared root cause."
                ),
                criteria={
                    "likely_duplicate": "The same symptom, feature, and conditions are described",
                    "different": "The symptoms, features, or conditions differ materially",
                    "unclear": "There is too little information to compare the reports",
                },
            ),
        },
    )

answer = response.choices["relationship"]
if answer.choice == "likely_duplicate" and answer.confidence >= 0.9:
    print("Suggest linking issue 81 to issue 29 for maintainer review")
else:
    print("Keep the reports separate pending review")
```

The intended result is `likely_duplicate`. Similar symptoms can have different causes, so this example does not close either issue.

## Choose the smallest useful question

Use `Choice` when one label is enough. Use separate `Noul` questions when multiple labels can apply. Use `Score` when the answer belongs on an ordered scale.

Keep exact arithmetic, date comparisons, and permission checks in code. Jev 1.13 has documented weaknesses in numeric tasks and can be influenced by misleading input. Read the [model limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13) before using a result to trigger an action.

For a first experiment, pick one use case and label 20 examples yourself. Run the script on them and inspect the disagreements. That is a starting check, not enough evidence for high-impact automation.

API details checked against TypeSafe's official documentation on 21 September 2026. The examples have been checked with SDK 0.7.0 and simulated API responses; live model accuracy has not been measured.
