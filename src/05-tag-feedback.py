"""Give product feedback one or more tags."""

# Thresholds are teaching examples. Test them on your own data.

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
