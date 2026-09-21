"""Suggest a possible duplicate for maintainer review."""

# Thresholds are teaching examples. Test them on your own data.

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
