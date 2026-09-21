"""Find passages that help answer a question."""

# Thresholds are teaching examples. Test them on your own data.

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
