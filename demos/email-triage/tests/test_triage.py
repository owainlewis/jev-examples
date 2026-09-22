import base64
import json
import sqlite3
import sys
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gmail
import triage

MESSAGE = {
    "id": "1",
    "sender": "sender@example.com",
    "subject": "Hello",
    "body": "Can you send your sponsorship rates?",
}


def answer(tokens=1000):
    return dict(
        triage.decision(
            "sponsorship",
            {"sponsorship": 1, "business_enquiry": 0, "ai_engineer": 0, "other": 0},
            0.9,
        ),
        input_tokens=tokens,
    )


class TriageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "results.sqlite3"

    def test_cache_and_new_call_cost(self):
        classifier = Mock(return_value=answer())
        first = triage.run([MESSAGE], "test", self.path, "demo", classifier)
        second = triage.run([MESSAGE], "test", self.path, "demo", classifier)
        self.assertEqual(classifier.call_count, 1)
        self.assertAlmostEqual(first["usage"]["estimated_jev_cost_usd"], 0.000042)
        self.assertEqual(second["usage"]["estimated_jev_cost_usd"], 0)
        self.assertEqual(second["counts"]["cached"], 1)
        self.assertEqual(second["messages"][0]["input_tokens"], 1000)
        self.assertNotIn(MESSAGE["body"].encode(), self.path.read_bytes())
        self.assertNotIn(MESSAGE["sender"].encode(), self.path.read_bytes())

    def test_cache_namespace_and_content(self):
        classifier = Mock(return_value=answer())
        triage.run([MESSAGE], "test", self.path, "demo", classifier)
        triage.run([MESSAGE], "test", self.path, "gmail:account", classifier)
        triage.run(
            [dict(MESSAGE, body="Changed")], "test", self.path, "demo", classifier
        )
        self.assertEqual(classifier.call_count, 3)
        before = triage.fingerprint(MESSAGE)
        with patch.object(triage, "ACTION_QUESTION", "New question"):
            self.assertNotEqual(before, triage.fingerprint(MESSAGE))

    def test_failed_call_is_not_cached_or_reported_free(self):
        classifier = Mock(side_effect=RuntimeError("SECRET"))
        result = triage.run([MESSAGE], "test", self.path, "demo", classifier)
        self.assertIsNone(result["usage"]["estimated_jev_cost_usd"])
        self.assertFalse(result["usage"]["cost_complete"])
        self.assertNotIn("SECRET", json.dumps(result))
        retry = triage.run(
            [MESSAGE], "test", self.path, "demo", Mock(return_value=answer())
        )
        self.assertEqual(retry["counts"]["classified"], 1)

    def test_missing_usage_is_unknown(self):
        result = triage.run(
            [MESSAGE], "test", self.path, "demo", Mock(return_value=answer(None))
        )
        self.assertIsNone(result["usage"]["estimated_jev_cost_usd"])
        self.assertEqual(result["usage"]["calls_missing_usage"], 1)

    def test_empty_and_oversized_messages_are_not_sent(self):
        classifier = Mock()
        result = triage.run(
            [dict(MESSAGE, body=""), dict(MESSAGE, id="2", body="x" * 25000)],
            "test",
            self.path,
            "demo",
            classifier,
        )
        classifier.assert_not_called()
        self.assertEqual(result["counts"]["rejected"], 2)

    def test_probabilities_and_thresholds(self):
        probs = {
            "sponsorship": 0.8,
            "business_enquiry": 0.2,
            "ai_engineer": 0,
            "other": 0,
        }
        self.assertFalse(triage.decision("sponsorship", probs, 0.8)["needs_review"])
        self.assertEqual(
            triage.decision("sponsorship", probs, 0.2)["action"], "no_action"
        )
        self.assertTrue(triage.decision("sponsorship", probs, 0.5)["needs_review"])
        for bad in [float("nan"), float("inf"), True, -1, 2]:
            with self.assertRaises(ValueError):
                triage.decision("sponsorship", probs, bad)
        with self.assertRaises(ValueError):
            triage.decision("business_enquiry", probs, 0.8)
        with self.assertRaises(ValueError):
            triage.decision("sponsorship", {**probs, "other": 0.5}, 0.8)

    def test_duplicate_ids_rejected_before_calls(self):
        classifier = Mock()
        with self.assertRaises(ValueError):
            triage.run([MESSAGE, MESSAGE], "test", self.path, "demo", classifier)
        classifier.assert_not_called()

    def test_busy_cache_makes_no_calls(self):
        triage.run([], "test", self.path, "demo")
        classifier = Mock()
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            with self.assertRaises(sqlite3.OperationalError):
                triage.run([MESSAGE], "test", self.path, "demo", classifier)
        classifier.assert_not_called()


class GmailTests(unittest.TestCase):
    def raw(self, message):
        return {
            "id": "gmail1",
            "raw": base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("="),
        }

    def test_mime_prefers_plain_and_ignores_attachment(self):
        message = EmailMessage()
        message["Subject"] = "Workshop proposal"
        message["From"] = "name@example.com"
        message.set_content("Plain body")
        message.add_alternative("<p>HTML body</p>", subtype="html")
        message.add_attachment(
            b"Attachment secret",
            maintype="application",
            subtype="octet-stream",
            filename="secret.bin",
        )
        result = gmail.decode_message(self.raw(message))
        self.assertEqual(result["subject"], "Workshop proposal")
        self.assertIn("Plain body", result["body"])
        self.assertNotIn("Attachment", result["body"])
        self.assertNotIn("HTML", result["body"])

    def test_html_fallback_strips_script(self):
        message = EmailMessage()
        message.set_content(
            "<style>hidden</style><p>Hello</p><script>evil</script><p>World</p>",
            subtype="html",
        )
        result = gmail.decode_message(self.raw(message))
        self.assertIn("Hello", result["body"])
        self.assertNotIn("evil", result["body"])
        self.assertNotIn("hidden", result["body"])

    def test_pagination_and_partial_flag(self):
        session = Mock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=False)
        payloads = [
            {"emailAddress": "me@example.com"},
            {"messages": [{"id": "a"}], "nextPageToken": "page2"},
            {"id": "a"},
            {"messages": [{"id": "b"}], "nextPageToken": "page3"},
            {"id": "b"},
        ]
        session.get.side_effect = [Mock(json=Mock(return_value=p)) for p in payloads]
        with (
            patch.object(
                gmail.Credentials,
                "from_authorized_user_file",
                return_value=Mock(valid=True),
            ),
            patch.object(gmail, "AuthorizedSession", return_value=session),
            patch.object(gmail, "decode_message", side_effect=lambda item: item),
        ):
            messages, account, more = gmail.fetch(Path("unused"), 7, 2)
        self.assertEqual(messages, [{"id": "a"}, {"id": "b"}])
        self.assertEqual(account, "me@example.com")
        self.assertTrue(more)
        self.assertEqual(
            session.get.call_args_list[3].kwargs["params"]["pageToken"], "page2"
        )
        session.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
