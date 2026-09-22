import copy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from time import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.app import create_app
from backend.classifier import DEPARTMENTS, classify, policy, questions
from backend.store import Store, LEASE_SECONDS

HEADERS = {"X-Demo-Request": "support-desk"}
ANSWERS = {
    "department": {
        "choice": "it_support",
        "confidence": 0.1,
        "probabilities": {
            "hr": 0.01,
            "finance": 0.01,
            "engineering": 0.03,
            "it_support": 0.94,
            "other": 0.01,
        },
    },
    "priority": {
        "choice": "high",
        "confidence": 0.99,
        "probabilities": {"low": 0.01, "normal": 0.09, "high": 0.89, "critical": 0.01},
    },
}


def result():
    answers = copy.deepcopy(ANSWERS)
    return {"raw": {"answers": answers}, "elapsed_ms": 123.4, "policy": policy(answers)}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "desk.sqlite3"
        self.calls = []

        def provider(ticket):
            self.calls.append(ticket)
            return result()

        self.app = create_app(self.path, provider)
        self.client = TestClient(self.app, headers=HEADERS)
        self.addCleanup(self.client.close)
        self.store = self.app.state.store

    def create(self):
        return self.client.post(
            "/api/tickets",
            json={
                "subject": "GitHub access",
                "body": "My account is locked. I cannot work.",
            },
        )

    def test_creation_automatically_classifies_once_and_persists(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)
        ticket = response.json()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(ticket["status"], "succeeded")
        self.assertEqual(ticket["classification"]["department"]["choice"], "it_support")
        self.assertEqual(ticket["classification"]["department"]["probability"], 0.94)
        self.assertEqual(ticket["classification"]["priority"]["choice"], "high")
        self.assertFalse(ticket["classification"]["review_required"])
        self.assertEqual(
            Store(self.path).get(ticket["id"])["routing"], ticket["classification"]
        )

    def test_startup_and_reads_do_not_spend_api_calls(self):
        self.assertEqual(self.client.get("/api/tickets").json(), [])
        self.client.get("/api/config")
        self.assertEqual(self.calls, [])

    def test_category_probability_not_confidence_controls_review(self):
        accepted = policy(ANSWERS)
        self.assertFalse(
            accepted["department"]["needs_review"]
        )  # confidence .1, probability .94
        answers = copy.deepcopy(ANSWERS)
        answers["priority"]["probabilities"] = {
            "low": 0.01,
            "normal": 0.2,
            "high": 0.78,
            "critical": 0.01,
        }
        reviewed = policy(answers)
        self.assertTrue(reviewed["review_required"])
        self.assertTrue(reviewed["priority"]["needs_review"])
        self.assertFalse(reviewed["department"]["needs_review"])
        self.assertEqual(reviewed["priority"]["choice"], "high")
        self.assertEqual(reviewed["priority"]["probability"], 0.78)

    def test_exact_threshold_and_other_are_not_automatically_reviewed(self):
        answers = copy.deepcopy(ANSWERS)
        answers["department"]["probabilities"] = {
            "hr": 0.05,
            "finance": 0.05,
            "engineering": 0.05,
            "it_support": 0.05,
            "other": 0.8,
        }
        decision = policy(answers)
        self.assertEqual(decision["department"]["choice"], "other")
        self.assertFalse(decision["review_required"])
        answers["department"]["probabilities"]["other"] = 0.7999
        self.assertTrue(policy(answers)["department"]["needs_review"])

    def test_selects_largest_probability_instead_of_trusting_choice_label(self):
        answers = copy.deepcopy(ANSWERS)
        answers["department"]["choice"] = "hr"
        self.assertEqual(policy(answers)["department"]["choice"], "it_support")

    def test_questions_use_two_choice_types_and_all_categories(self):
        query = questions()
        self.assertEqual(set(query), {"department", "priority"})
        self.assertTrue(
            all(type(value).__name__ == "Choice" for value in query.values())
        )
        self.assertEqual(set(query["department"].criteria), set(DEPARTMENTS))
        self.assertEqual(
            set(query["priority"].criteria), {"low", "normal", "high", "critical"}
        )
        with patch("backend.classifier.TypeSafeClient") as client:
            call = client.return_value.__enter__.return_value.system_one
            call.return_value.model_dump.return_value = {"answers": ANSWERS}
            classify({"subject": "Hello", "body": "Help", "customer": "Private name"})
            self.assertEqual(call.call_count, 1)
            self.assertEqual(
                call.call_args.kwargs["state"], {"subject": "Hello", "body": "Help"}
            )
            self.assertEqual(call.call_args.kwargs["questions"], query)

    def test_auto_failure_preserves_ticket_and_retry_succeeds(self):
        def fail(ticket):
            raise RuntimeError("private-key")

        with TestClient(create_app(self.path, fail), headers=HEADERS) as client:
            response = client.post(
                "/api/tickets", json={"subject": "Help", "body": "Need access"}
            )
        saved = response.json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(saved["status"], "failed")
        self.assertIsNone(saved["classification"])
        self.assertNotIn("private-key", response.text)
        retry = self.client.post(f"/api/tickets/{saved['id']}/runs", json={})
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["status"], "succeeded")
        self.assertEqual(len(self.store.get(saved["id"])["runs"]), 2)

    def test_concurrent_run_and_reset_are_rejected(self):
        entered, release = Event(), Event()
        ticket = self.store.create(
            {"subject": "Hello", "body": "Help", "customer": "Sam"}
        )

        def slow(ticket):
            entered.set()
            if not release.wait(5):
                raise TimeoutError()
            return result()

        with (
            TestClient(create_app(self.path, slow), headers=HEADERS) as client,
            ThreadPoolExecutor() as pool,
        ):
            pending = pool.submit(
                client.post, f"/api/tickets/{ticket['id']}/runs", json={}
            )
            try:
                self.assertTrue(entered.wait(3))
                self.assertEqual(
                    self.client.post(
                        f"/api/tickets/{ticket['id']}/runs", json={}
                    ).status_code,
                    409,
                )
            finally:
                release.set()
            self.assertEqual(pending.result().status_code, 200)

    def test_expired_run_cannot_overwrite_newer_result(self):
        ticket = self.store.create(
            {"subject": "Hello", "body": "Help", "customer": "Sam"}
        )
        old = self.store.claim(ticket["id"], "triage")
        with self.store.connection() as db:
            db.execute(
                "UPDATE runs SET started_at=? WHERE id=?",
                (time() - LEASE_SECONDS - 1, old),
            )
        new = self.store.claim(ticket["id"], "triage")
        self.assertTrue(self.store.finish(new, result()))
        self.assertFalse(self.store.finish(old, result()))
        self.assertEqual(
            self.store.get(ticket["id"])["routing"]["priority"]["choice"], "high"
        )

    def test_legacy_tickets_preserved_without_mislabeling_old_results(self):
        old = self.store.create(
            {"subject": "Old ticket", "body": "Keep this message", "customer": "Sam"}
        )
        with self.store.connection() as db:
            db.execute(
                "UPDATE tickets SET routing=? WHERE id=?",
                ('{"team":"billing","priority":"standard"}', old["id"]),
            )
        saved = self.client.get("/api/tickets").json()[0]
        self.assertEqual(saved["body"], "Keep this message")
        self.assertIsNone(saved["classification"])
        self.assertEqual(saved["status"], "unclassified")
        self.assertEqual(
            self.client.post(f"/api/tickets/{old['id']}/runs", json={}).json()[
                "classification"
            ]["department"]["choice"],
            "it_support",
        )

    def test_validation_and_local_boundary(self):
        self.assertEqual(
            self.client.post(
                "/api/tickets", json={"subject": " ", "body": "hi"}
            ).status_code,
            422,
        )
        self.assertEqual(
            self.client.post(
                "/api/tickets",
                json={"subject": "Hi", "body": "hi"},
                headers={"X-Demo-Request": ""},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(
                "/api/config", headers={"host": "evil.example"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post("/api/tickets/missing/runs", json={}).status_code, 404
        )
        with patch.dict("os.environ", {"TYPESAFE_API_KEY": "private-test-key"}):
            self.assertNotIn("private-test-key", self.client.get("/api/config").text)

    def test_invalid_distribution_rejected(self):
        answers = copy.deepcopy(ANSWERS)
        answers["department"]["probabilities"]["hr"] = float("nan")
        with self.assertRaises(ValueError):
            policy(answers)


if __name__ == "__main__":
    unittest.main()
