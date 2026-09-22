import ast
import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from time import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.classifier import MODES, policy, python_example, questions, classify
from backend.store import Store, LEASE_SECONDS

ANSWERS = {
    "team": {
        "choice": "billing",
        "probabilities": {
            "billing": 0.97,
            "technical": 0.01,
            "account": 0.01,
            "other": 0.01,
        },
        "confidence": 0.95,
    },
    "refund_requested": {"noul": 0.99},
    "impact": {"score": 0.02, "probabilities": [0.99, 0, 0.01], "confidence": 0.95},
    "impact_stated": {"noul": 0.99},
}
HEADERS = {"X-Demo-Request": "support-desk"}


def result(mode):
    answers = {key: copy.deepcopy(ANSWERS[key]) for key in MODES[mode]}
    return {
        "raw": {"answers": answers},
        "elapsed_ms": 123.4,
        "policy": policy(answers) if mode == "combined" else None,
    }


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "desk.sqlite3"
        self.calls = []

        def provider(ticket, mode):
            self.calls.append((ticket, mode))
            return result(mode)

        self.app = create_app(self.path, provider)
        self.client = TestClient(self.app, headers=HEADERS)
        self.addCleanup(self.client.close)
        self.identifier = self.client.get("/api/tickets").json()[0]["id"]

    def run_mode(self, mode):
        return self.client.post(
            f"/api/tickets/{self.identifier}/runs", json={"mode": mode}
        )

    def test_preview_modes_do_not_route_and_only_call_on_run(self):
        self.client.get("/api/config")
        self.client.get("/api/tickets")
        self.assertEqual(self.calls, [])
        for mode in ["choice", "noul", "score"]:
            ticket = self.run_mode(mode).json()
            self.assertIsNone(ticket["routing"])
            self.assertEqual(
                list(ticket["runs"][0]["result"]["raw"]["answers"]), MODES[mode]
            )
        self.assertEqual(len(self.calls), 3)

    def test_combined_routes_and_persists(self):
        ticket = self.run_mode("combined").json()
        self.assertEqual(ticket["routing"]["team"], "billing")
        self.assertEqual(ticket["routing"]["priority"], "standard")
        self.assertEqual(
            Store(self.path).get(self.identifier)["routing"], ticket["routing"]
        )

    def test_manual_correction_survives_future_runs(self):
        self.run_mode("combined")
        correction = {"team": "account", "priority": "urgent"}
        response = self.client.patch(
            f"/api/tickets/{self.identifier}/correction", json=correction
        )
        self.assertEqual(response.status_code, 200)
        ticket = self.run_mode("combined").json()
        self.assertEqual(ticket["correction"], correction)
        self.assertEqual(ticket["routing"]["team"], "billing")

    def test_policy_reviews_uncertainty_and_missing_impact(self):
        for key, field, value in [
            ("impact_stated", "noul", 0.3),
            ("team", "confidence", 0.4),
            ("impact", "confidence", 0.4),
            ("team", "choice", "other"),
        ]:
            answers = copy.deepcopy(ANSWERS)
            answers[key][field] = value
            self.assertTrue(policy(answers)["review_required"])
            self.assertEqual(policy(answers)["priority"], "needs_review")
        answers = copy.deepcopy(ANSWERS)
        answers["impact"]["score"] = 1.9
        self.assertEqual(policy(answers)["priority"], "urgent")

    def test_create_and_reset(self):
        response = self.client.post(
            "/api/tickets",
            json={"subject": " Test ", "body": "Hello", "customer": "Sam"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["subject"], "Test")
        self.assertEqual(response.json()["routing"]["team"], "billing")
        self.assertEqual(response.json()["runs"][0]["mode"], "combined")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(self.client.get("/api/tickets").json()), 5)
        tickets = self.client.post("/api/reset", json={}).json()
        self.assertEqual(len(tickets), 4)
        self.assertTrue(all(not t["runs"] and t["routing"] is None for t in tickets))

    def test_validation_and_local_request_boundary(self):
        self.assertEqual(
            self.client.post(
                "/api/tickets", json={"subject": " ", "body": "hi"}
            ).status_code,
            422,
        )
        self.assertEqual(self.run_mode("unknown").status_code, 422)
        self.assertEqual(
            self.client.post(
                "/api/reset", json={}, headers={"X-Demo-Request": ""}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                "/api/reset", content="{}", headers={"Content-Type": "text/plain"}
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
            self.client.post(
                "/api/tickets/missing/runs", json={"mode": "choice"}
            ).status_code,
            404,
        )

    def test_failure_preserves_history_and_sanitizes_error(self):
        self.run_mode("choice")

        def fail(ticket, mode):
            raise RuntimeError("secret-api-key-and-private-data")

        with TestClient(create_app(self.path, fail), headers=HEADERS) as client:
            response = client.post(
                f"/api/tickets/{self.identifier}/runs", json={"mode": "choice"}
            )
            self.assertEqual(response.status_code, 502)
            self.assertNotIn("secret", response.text)
        self.assertEqual(
            [r["status"] for r in self.app.state.store.get(self.identifier)["runs"]],
            ["failed", "succeeded"],
        )
        self.assertEqual(self.run_mode("choice").status_code, 200)

    def test_concurrent_request_and_reset_rejected_correction_preserved(self):
        entered, release = Event(), Event()

        def slow(ticket, mode):
            entered.set()
            if not release.wait(5):
                raise TimeoutError()
            return result(mode)

        with (
            TestClient(create_app(self.path, slow), headers=HEADERS) as client,
            ThreadPoolExecutor() as pool,
        ):
            pending = pool.submit(
                client.post,
                f"/api/tickets/{self.identifier}/runs",
                json={"mode": "combined"},
            )
            try:
                self.assertTrue(entered.wait(3))
                self.assertEqual(self.run_mode("choice").status_code, 409)
                self.assertEqual(
                    self.client.post("/api/reset", json={}).status_code, 409
                )
                correction = {"team": "technical", "priority": "urgent"}
                self.client.patch(
                    f"/api/tickets/{self.identifier}/correction", json=correction
                )
            finally:
                release.set()
            self.assertEqual(pending.result().json()["correction"], correction)

    def test_expired_claim_cannot_overwrite_new_result(self):
        store = self.app.state.store
        old = store.claim(self.identifier, "combined")
        with store.connection() as db:
            db.execute(
                "UPDATE runs SET started_at=? WHERE id=?",
                (time() - LEASE_SECONDS - 1, old),
            )
        new = store.claim(self.identifier, "combined")
        self.assertTrue(store.finish(new, result("combined")))
        stale = result("combined")
        stale["policy"]["team"] = "other"
        self.assertFalse(store.finish(old, stale))
        self.assertEqual(store.get(self.identifier)["routing"]["team"], "billing")

    def test_question_definitions_and_generated_examples(self):
        expected = {
            "choice": {"team": "Choice"},
            "noul": {"refund_requested": "Noul"},
            "score": {"impact": "Score"},
            "combined": {
                "team": "Choice",
                "refund_requested": "Noul",
                "impact": "Score",
                "impact_stated": "Noul",
            },
        }
        for mode, types in expected.items():
            self.assertEqual(
                {key: type(q).__name__ for key, q in questions(mode).items()}, types
            )
            code = python_example(mode)
            ast.parse(code)
            scope = {}
            exec(code.split("with TypeSafeClient")[0], scope)
            self.assertEqual(scope["questions"], questions(mode))

    def test_sdk_call_uses_exact_mode_and_ticket_state(self):
        with patch("backend.classifier.TypeSafeClient") as client:
            response = client.return_value.__enter__.return_value.system_one
            response.return_value.model_dump.return_value = {"answers": ANSWERS}
            for mode in MODES:
                classify(
                    {
                        "subject": "Hello",
                        "body": "Refund please",
                        "customer": "Private name",
                    },
                    mode,
                )
                self.assertEqual(
                    response.call_args.kwargs["state"],
                    {"subject": "Hello", "body": "Refund please"},
                )
                self.assertEqual(
                    response.call_args.kwargs["questions"], questions(mode)
                )

    def test_reset_after_create_commit_returns_complete_snapshot(self):
        store = self.app.state.store
        original = store.connection
        reset_once = [True]

        @contextmanager
        def connection():
            with original() as db:
                yield db
            if reset_once[0]:
                reset_once[0] = False
                store.reset()

        with patch.object(store, "connection", connection):
            saved = store.create(
                {"subject": "Saved", "body": "A real ticket", "customer": "Sam"}
            )
        self.assertEqual(saved["subject"], "Saved")
        self.assertEqual(saved["runs"], [])
        self.assertEqual(len(store.list()), 4)

    def test_reset_between_run_lookup_and_claim_returns_not_found(self):
        store = self.app.state.store
        original = store.claim

        def reset_before_claim(identifier, mode):
            store.reset()
            return original(identifier, mode)

        with patch.object(store, "claim", reset_before_claim):
            self.assertEqual(self.run_mode("choice").status_code, 404)
        self.assertEqual(self.calls, [])

    def test_correction_after_reset_returns_not_found(self):
        self.app.state.store.reset()
        response = self.client.patch(
            f"/api/tickets/{self.identifier}/correction",
            json={"team": "billing", "priority": "standard"},
        )
        self.assertEqual(response.status_code, 404)

    def test_automatic_failure_returns_saved_ticket_and_can_retry(self):
        def fail(ticket, mode):
            raise RuntimeError("private-key")

        with TestClient(create_app(self.path, fail), headers=HEADERS) as client:
            response = client.post(
                "/api/tickets", json={"subject": "Refund", "body": "Please refund me."}
            )
        self.assertEqual(response.status_code, 201)
        saved = response.json()
        self.assertEqual(saved["runs"][0]["status"], "failed")
        self.assertIsNone(saved["routing"])
        self.assertNotIn("private-key", response.text)
        retry = self.client.post(
            f"/api/tickets/{saved['id']}/runs", json={"mode": "combined"}
        )
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["routing"]["team"], "billing")

    def test_config_never_returns_api_key(self):
        with patch.dict("os.environ", {"TYPESAFE_API_KEY": "private-test-key"}):
            response = self.client.get("/api/config")
            self.assertTrue(response.json()["configured"])
            self.assertNotIn("private-test-key", response.text)


if __name__ == "__main__":
    unittest.main()
