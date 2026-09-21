"""Noul: a yes/no judgment returned as a probability."""

from dotenv import load_dotenv
from typesafe_sdk import Noul, TypeSafeClient

load_dotenv()
ticket = "I was charged twice. Please refund the duplicate payment."

with TypeSafeClient(model="jev-1.13.0", timeout=30.0) as client:
    response = client.system_one(
        state=ticket,
        questions={
            "refund_requested": Noul(
                instructions="Does the customer explicitly request money to be returned?"
            ),
        },
    )

probability = response.nouls["refund_requested"].noul
print("Probability of a refund request:", probability)
# Teaching thresholds, not a measured guarantee. No refund is executed.
if probability >= 0.9:
    print("Next step: check the refund policy.")
elif probability <= 0.1:
    print("Next step: continue normal support.")
else:
    print("Next step: review what the customer is asking for.")
