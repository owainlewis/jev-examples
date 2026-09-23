"""Read-only Gmail adapter. OAuth is interactive only when explicitly authorized."""

import base64
import email
import email.policy
import os
from html.parser import HTMLParser

from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


def save_token(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as file:
        file.write(text)
    os.chmod(temporary, 0o600)
    temporary.replace(path)


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        elif tag in ("p", "div", "br", "li", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def decode_message(item):
    raw = item["raw"]
    parsed = email.message_from_bytes(
        base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)),
        policy=email.policy.default,
    )
    body = parsed.get_body(preferencelist=("plain", "html"))
    text = body.get_content() if body is not None else ""
    if body is not None and body.get_content_type() == "text/html":
        parser = TextOnly()
        parser.feed(text)
        text = " ".join(parser.parts)
    return {
        "id": item["id"],
        "sender": str(parsed.get("From", "")),
        "subject": str(parsed.get("Subject", "")),
        "body": text,
    }


def fetch(token_file, days, limit):
    credentials = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if not credentials.valid:
        if not credentials.refresh_token:
            raise ValueError("Authorize Gmail first")
        credentials.refresh(Request())
        save_token(token_file, credentials.to_json())
    messages = []
    with AuthorizedSession(credentials) as session:

        def get(path, params=None):
            response = session.get(BASE + path, params=params, timeout=30)
            response.raise_for_status()
            return response.json()

        account = get("/profile")["emailAddress"]
        token = None
        while len(messages) < limit:
            params = {
                "q": f"newer_than:{days}d -in:sent -in:drafts",
                "maxResults": min(100, limit - len(messages)),
            }
            if token:
                params["pageToken"] = token
            page = get("/messages", params)
            for item in page.get("messages", []):
                messages.append(
                    decode_message(get("/messages/" + item["id"], {"format": "raw"}))
                )
            token = page.get("nextPageToken")
            if not token:
                break
    return messages, account, bool(token)
