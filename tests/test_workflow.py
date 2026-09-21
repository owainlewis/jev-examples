import contextlib
import copy
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from jev_tutorial.app import create_app
from jev_tutorial.classifier import ticket_policy
from jev_tutorial.email_cli import classify_emails, load_inputs, main
from jev_tutorial.evaluate import summarize


def response_fixture():
    answers = {
        "team": {"choice": "technical", "confidence": .98,
                 "probabilities": {"technical": .98, "billing": .01, "other": .01}},
        "impact": {"score": 1, "confidence": 1, "probabilities": {"1": 1}},
        "impact_stated": {"noul": .99},
        "refund_requested": {"noul": .01},
    }
    return {"model": "controlled-test-response", "usage": {"input_tokens": 500},
            "elapsed_ms": 10, "answers": answers, "policy": ticket_policy(answers)}


class PolicyTests(unittest.TestCase):
    def test_clear_workaround_can_route(self):
        result = ticket_policy(response_fixture()["answers"])
        self.assertFalse(result["review_required"])
        self.assertEqual(result["priority"], "standard")

    def test_missing_impact_overrides_confident_score(self):
        answers = response_fixture()["answers"]
        answers["impact_stated"]["noul"] = .1
        self.assertTrue(ticket_policy(answers)["review_required"])
        self.assertEqual(ticket_policy(answers)["priority"], "needs_review")

    def test_uncertain_team_requires_review(self):
        answers = response_fixture()["answers"]
        answers["team"]["confidence"] = .79
        self.assertTrue(ticket_policy(answers)["review_required"])

    def test_blocked_and_refund_intent_are_distinct(self):
        answers = response_fixture()["answers"]
        answers["impact"]["score"] = 2
        answers["refund_requested"]["noul"] = .5
        result = ticket_policy(answers)
        self.assertEqual(result["priority"], "blocked")
        self.assertEqual(result["refund_intent"], "uncertain")


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "tickets.sqlite3"
        self.classify = Mock(return_value=response_fixture())
        self.app = create_app(self.database, self.classify)
        self.app.testing = True
        self.client = self.app.test_client()

    def post(self, path, **data):
        self.client.get("/")
        with self.client.session_transaction() as session:
            data["csrf_token"] = session["csrf_token"]
        return self.client.post(path, data=data, follow_redirects=True)

    def submit(self):
        return self.post("/tickets", subject="Export broken", body="I can use CSV instead.")

    def test_create_inspect_and_persist_across_restart(self):
        page = self.submit()
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Jev's assessment", page.data)
        self.assertIn(b"Technical", page.data)
        self.classify.assert_called_once_with({"subject": "Export broken", "body": "I can use CSV instead."})
        restarted = create_app(self.database, self.classify).test_client()
        self.assertIn(b"Export broken", restarted.get("/").data)

    def test_failure_keeps_ticket_and_retry_recovers(self):
        self.classify.side_effect = [TimeoutError("sensitive provider detail"), response_fixture()]
        failed = self.submit()
        self.assertIn(b"Ticket saved. Classification failed.", failed.data)
        self.assertNotIn(b"sensitive provider detail", failed.data)
        self.assertIn(b"Export broken", self.client.get("/?review=1").data)
        recovered = self.post("/tickets/1/retry")
        self.assertIn(b"Jev's assessment", recovered.data)
        self.assertNotIn(b"Export broken", self.client.get("/?review=1").data)

    def test_review_preserves_original_model_result_and_changes_filter(self):
        self.submit()
        page = self.post("/tickets/1/review", team="billing", priority="blocked")
        self.assertIn(b"Reviewed by you", page.data)
        self.assertIn(b"Technical", page.data)  # Original assessment remains visible.
        self.assertIn(b"Export broken", self.client.get("/?team=billing").data)
        self.assertNotIn(b"Export broken", self.client.get("/?team=technical").data)
        self.assertEqual(self.post("/tickets/1/retry").status_code, 409)

    def test_failed_ticket_can_be_manually_reviewed(self):
        self.classify.side_effect = TimeoutError()
        self.submit()
        self.post("/tickets/1/review", team="technical", priority="standard")
        self.assertNotIn(b"Export broken", self.client.get("/?review=1").data)

    def test_slow_classification_never_undoes_a_human_review(self):
        for fail in (False, True):
            with self.subTest(api_fails=fail):
                started, release = threading.Event(), threading.Event()

                def slow_classify(ticket):
                    started.set()
                    if not release.wait(5):
                        raise TimeoutError("Test did not release the request")
                    if fail:
                        raise TimeoutError()
                    result = response_fixture()
                    result["policy"]["review_required"] = True
                    return result

                app = create_app(Path(self.temp.name) / f"concurrent-{fail}.sqlite3", slow_classify)
                submitter, reviewer = app.test_client(), app.test_client()
                submitter.get("/")
                with submitter.session_transaction() as session:
                    token = session["csrf_token"]
                worker = threading.Thread(target=lambda: submitter.post("/tickets", data={
                    "subject": "Slow ticket", "body": "Something broke", "csrf_token": token,
                }))
                worker.start()
                try:
                    self.assertTrue(started.wait(5))
                    reviewer.get("/")
                    with reviewer.session_transaction() as session:
                        token = session["csrf_token"]
                    reviewed = reviewer.post("/tickets/1/review", data={
                        "team": "billing", "priority": "blocked", "csrf_token": token,
                    })
                    self.assertEqual(reviewed.status_code, 303)
                finally:
                    release.set()
                    worker.join(5)
                self.assertFalse(worker.is_alive())
                self.assertNotIn(b"Slow ticket", reviewer.get("/?review=1").data)
                self.assertIn(b"Reviewed by you", reviewer.get("/tickets/1").data)

    def test_invalid_submission_and_review_do_not_call_model(self):
        self.assertEqual(self.post("/tickets", subject=" ", body="empty subject").status_code, 400)
        self.classify.assert_not_called()
        self.submit()
        self.assertEqual(self.post("/tickets/1/review", team="invented", priority="standard").status_code, 400)

    def test_forms_reject_cross_site_posts_and_escape_ticket_text(self):
        self.assertEqual(self.client.post("/tickets", data={"subject": "x", "body": "y"}).status_code, 400)
        page = self.post("/tickets", subject="<script>alert(1)</script>", body="<img src=x onerror=alert(1)>")
        self.assertNotIn(b"<script>alert(1)</script>", page.data)
        self.assertIn(b"&lt;script&gt;", page.data)
        self.assertEqual(self.client.get("/", headers={"Host": "evil.example"}).status_code, 400)


class EmailTests(unittest.TestCase):
    def test_ids_are_preserved_and_other_is_not_automatically_review(self):
        client = Mock()
        client.system_one.return_value = SimpleNamespace(
            choices={"category": SimpleNamespace(choice="Other", confidence=.99, probabilities={"Other": .99})},
            nouls={"action_requested": SimpleNamespace(noul=.02)},
        )
        result = classify_emails([{"id": "001", "subject": "Receipt", "body": "Thanks", "private": "excluded"}],
                                {"Other": "Other messages"}, client)
        self.assertEqual(result[0]["id"], "001")
        self.assertFalse(result[0]["review_required"])
        self.assertEqual(client.system_one.call_args.kwargs["state"], {"subject": "Receipt", "body": "Thanks"})

    def test_duplicate_ids_fail_before_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            record = {"id": "1", "subject": "Test", "body": "Test"}
            (path / "emails.json").write_text(json.dumps([record, record]))
            (path / "categories.json").write_text('{"Other": "Other messages"}')
            with self.assertRaisesRegex(ValueError, "unique"):
                load_inputs(path / "emails.json", path / "categories.json")

    def test_batch_failure_has_nonzero_exit_and_no_partial_json(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("sys.argv", ["email_cli", "data/emails.json"]), \
                patch("jev_tutorial.email_cli.make_client") as client, \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            successful = SimpleNamespace(
                choices={"category": SimpleNamespace(choice="Other", confidence=.99, probabilities={"Other": .99})},
                nouls={"action_requested": SimpleNamespace(noul=.02)},
            )
            client.return_value.__enter__.return_value.system_one.side_effect = [successful, TimeoutError("secret")]
            self.assertEqual(main(), 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("TimeoutError", stderr.getvalue())
        self.assertNotIn("secret", stderr.getvalue())


class EvaluationTests(unittest.TestCase):
    def test_failures_and_reviews_are_not_counted_as_automatic_successes(self):
        result = response_fixture()
        review = copy.deepcopy(result)
        review["policy"]["review_required"] = True
        stats = summarize([
            {"result": result, "team_correct": False},
            {"result": review, "team_correct": True},
            {"error_type": "TimeoutError"},
        ])
        self.assertEqual(stats["api_failures"], 1)
        self.assertEqual(stats["team_accuracy_on_successful"], .5)
        self.assertEqual(stats["automation_coverage"], 1 / 3)
        self.assertEqual(stats["automatic_team_error_rate"], 1)

    def test_all_failures_report_unknown_accuracy(self):
        stats = summarize([{"error_type": "TimeoutError"}])
        self.assertIsNone(stats["team_accuracy_on_successful"])
        self.assertIsNone(stats["automatic_team_error_rate"])
        self.assertIsNone(stats["median_ms"])


if __name__ == "__main__":
    unittest.main()
