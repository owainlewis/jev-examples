"""Noul: a yes/no judgment returned as a probability."""

from dotenv import load_dotenv
from typesafe_sdk import Noul, TypeSafeClient

load_dotenv()
ticket = "I cannot sign in to my workspace. Every attempt shows a server error, so I cannot access my projects."

with TypeSafeClient(model="jev-1.13.0", timeout=30.0) as client:
    response = client.system_one(
        state=ticket,
        questions={
            "access_blocked": Noul(
                instructions="Does the customer report being unable to access their workspace?"
            ),
        },
    )

probability = response.nouls["access_blocked"].noul
print("Probability that workspace access is blocked:", probability)
# Teaching thresholds, not a measured guarantee. This example only prints the next step.
if probability >= 0.9:
    print("Next step: send to the access support queue.")
elif probability <= 0.1:
    print("Next step: continue normal support.")
else:
    print("Next step: review whether workspace access is blocked.")
