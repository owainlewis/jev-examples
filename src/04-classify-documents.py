"""Suggest a folder for document text."""

# Thresholds are teaching examples. Test them on your own data.

from dotenv import load_dotenv
from typesafe_sdk import Choice, TypeSafeClient

load_dotenv()

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
