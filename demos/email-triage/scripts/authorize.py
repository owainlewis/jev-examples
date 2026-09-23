# /// script
# requires-python = ">=3.10"
# dependencies = ["google-auth-oauthlib==1.2.2", "requests==2.32.5"]
# ///
"""Authorize read-only Gmail access locally. Never run unattended."""

import argparse
from pathlib import Path

from gmail import SCOPES, save_token
from google_auth_oauthlib.flow import InstalledAppFlow

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--client-file", type=Path, required=True)
parser.add_argument(
    "--token-file",
    type=Path,
    default=Path.home() / ".config/email-triage/gmail-token.json",
)
args = parser.parse_args()
flow = InstalledAppFlow.from_client_secrets_file(str(args.client_file), SCOPES)
credentials = flow.run_local_server(port=0, timeout_seconds=180)
save_token(args.token_file, credentials.to_json())
print("Saved Gmail authorization. Email access is read-only.")
