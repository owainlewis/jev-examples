import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from backend.app import create_app

HEADERS = {"X-Demo-Request": "feedback-lens"}


class AppTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-secret"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.provider = Mock(return_value={"theme": {"choice": "reliability"}})
        self.client = TestClient(create_app(self.provider))

    def submit(self, feedback="PDF export fails.", **kwargs):
        return self.client.post(
            "/api/analyze", json={"feedback": feedback}, headers=HEADERS, **kwargs
        )

    def test_explicit_submission_only(self):
        config = self.client.get("/api/config")
        self.assertEqual(config.status_code, 200)
        self.assertTrue(config.json()["configured"])
        self.assertEqual(len(config.json()["examples"]), 4)
        self.assertNotIn("test-secret", config.text)
        self.provider.assert_not_called()
        result = self.submit("  PDF export fails.  ")
        self.assertEqual(result.status_code, 200)
        self.provider.assert_called_once_with("PDF export fails.")

    def test_invalid_input_never_calls_provider(self):
        for value in ["", "   ", "a" * 6001, None, 1, {"secret": "private"}]:
            with self.subTest(value_type=type(value).__name__):
                result = self.submit(value)
                self.assertEqual(result.status_code, 422)
                self.assertNotIn("private", result.text)
        self.assertEqual(self.submit("a" * 6000).status_code, 200)
        self.provider.assert_called_once()

    def test_provider_errors_are_sanitized_and_retry_releases_lock(self):
        self.provider.side_effect = [
            RuntimeError("test-secret private message"),
            {"ok": True},
        ]
        result = self.submit()
        self.assertEqual(result.status_code, 502)
        self.assertNotIn("test-secret", result.text)
        self.assertNotIn("private message", result.text)
        self.assertEqual(self.submit().status_code, 200)

    def test_missing_key(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": " "}):
            self.assertFalse(self.client.get("/api/config").json()["configured"])
            self.assertEqual(self.submit().status_code, 503)
        self.provider.assert_not_called()

    def test_cross_origin_requests_are_rejected(self):
        self.assertEqual(
            self.client.post("/api/analyze", json={"feedback": "x"}).status_code, 403
        )
        for headers in [
            {**HEADERS, "Origin": "https://evil.example"},
            {**HEADERS, "Origin": "null"},
            {**HEADERS, "Sec-Fetch-Site": "cross-site"},
        ]:
            self.assertEqual(
                self.client.post(
                    "/api/analyze", json={"feedback": "x"}, headers=headers
                ).status_code,
                403,
            )
        self.assertEqual(
            self.client.post(
                "/api/analyze", data="feedback=x", headers=HEADERS
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.options(
                "/api/analyze", headers={"Origin": "https://evil.example"}
            ).status_code,
            405,
        )
        self.assertEqual(
            self.client.get(
                "/api/config", headers={"Host": "evil.example"}
            ).status_code,
            400,
        )
        self.provider.assert_not_called()
        self.assertEqual(
            self.client.post(
                "/api/analyze",
                json={"feedback": "x"},
                headers={**HEADERS, "Origin": "http://testserver"},
            ).status_code,
            200,
        )

    def test_only_frontend_is_public(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Feedback Lens", page.text)
        self.assertIn("frame-ancestors 'none'", page.headers["Content-Security-Policy"])
        self.assertEqual(page.headers["Cache-Control"], "no-store")
        for path in ["/.env", "/backend/app.py", "/pyproject.toml"]:
            self.assertEqual(self.client.get(path).status_code, 404)
        for path in ["/app.mjs", "/policy.mjs", "/style.css", "/mark.svg"]:
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_concurrent_request_rejected_without_second_provider_call(self):
        entered, release = Event(), Event()

        def slow_provider(text):
            entered.set()
            release.wait(timeout=5)
            return {"ok": True}

        self.provider.side_effect = slow_provider
        with ThreadPoolExecutor() as pool:
            pending = pool.submit(self.submit)
            try:
                self.assertTrue(entered.wait(timeout=5))
                self.assertEqual(self.submit().status_code, 409)
                self.provider.assert_called_once()
            finally:
                release.set()
            self.assertEqual(pending.result().status_code, 200)


if __name__ == "__main__":
    unittest.main()
