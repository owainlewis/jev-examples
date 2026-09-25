"""Noul: a yes/no judgment returned as a probability."""

from dotenv import load_dotenv
from typesafe_sdk import Noul, TypeSafeClient

load_dotenv()

ticket = "Hello how are you doing."

with TypeSafeClient(model="jev-1.13.0", timeout=30.0) as client:
    response = client.system_one(
        state=ticket,
        questions={
            "contains_pii": Noul(
                instructions="Does the customer request contain personally identifiable information (PII)?"
            ),
        },
    )

probability = response.nouls["contains_pii"].noul
contains_pii = probability > 0.5
print("Probability that the request contains PII:", probability)
# A teaching threshold, not a measured guarantee of PII detection.
print("Contains PII (probability > 0.5):", contains_pii)
