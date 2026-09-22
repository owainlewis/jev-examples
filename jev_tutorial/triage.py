"""Combine the questions and inspect the application's policy."""

import json

from .classifier import classify_ticket


def main():
    ticket = {
        "subject": "Export is broken",
        "body": "PDF export fails. I can finish today's report using CSV instead.",
    }
    print(json.dumps(classify_ticket(ticket), indent=2))


if __name__ == "__main__":
    main()
