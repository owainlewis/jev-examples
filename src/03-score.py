"""Score: place a ticket on an ordered rubric."""

from dotenv import load_dotenv
from typesafe_sdk import Score, TypeSafeClient

load_dotenv()
ticket = "The PDF export fails. I can finish today's report using CSV instead."

with TypeSafeClient(model="jev-1.13.0", timeout=30.0) as client:
    response = client.system_one(
        state=ticket,
        questions={
            "impact": Score(
                instructions="How much does the reported problem block the customer's work?",
                criteria=[
                    "The customer can complete their work without a workaround.",
                    "The customer can complete their work using a workaround.",
                    "The customer cannot complete their work and has no workaround.",
                ],
            ),
        },
    )

answer = response.scores["impact"]
print("Impact:", answer.score, "out of 2")
print("Levels:", answer.legend)
print("Probabilities:", answer.probabilities)
print("Confidence:", answer.confidence)
# A fractional score is a weighted position, not a percentage of customers.
