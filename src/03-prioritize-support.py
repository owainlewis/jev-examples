"""Score how much a support problem blocks the customer."""

# Thresholds are teaching examples. Test them on your own data.

from dotenv import load_dotenv
from typesafe_sdk import Score, TypeSafeClient

load_dotenv()

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
