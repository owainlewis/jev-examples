import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("router", ROOT / "scripts/route.py")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.config = router.load_config(ROOT / "models.json")

    def test_each_class_uses_configured_model(self):
        for tier in router.TIERS:
            with self.subTest(tier=tier):
                probabilities = {t: 0.9 if t == tier else 0.05 for t in router.TIERS}
                result = router.select_route(self.config, tier, probabilities)
                self.assertEqual(result["model"], self.config["routes"][tier]["model"])
                self.assertEqual(
                    result["reasoning"], self.config["routes"][tier]["reasoning"]
                )
                self.assertEqual(result["reason"], "jev")

    def test_uncertain_routine_uses_complex_without_relabeling(self):
        result = router.select_route(
            self.config, "routine", {"routine": 0.6, "standard": 0.3, "complex": 0.1}
        )
        self.assertEqual(result["route"], "complex")
        self.assertEqual(result["classification"], "routine")
        self.assertEqual(result["probability"], 0.6)
        self.assertEqual(result["reason"], "low_probability")

    def test_threshold_is_inclusive(self):
        result = router.select_route(
            self.config, "routine", {"routine": 0.8, "standard": 0.1, "complex": 0.1}
        )
        self.assertEqual(result["route"], "routine")

    def test_provider_error_falls_back_without_leaking(self):
        def fail(*args):
            raise RuntimeError("secret-key private-task")

        result = router.route("private-task", self.config, "secret-key", fail)
        self.assertEqual(result["route"], "complex")
        self.assertIsNone(result["probability"])
        self.assertNotIn("secret", json.dumps(result))
        self.assertNotIn("private", json.dumps(result))

    def test_invalid_answers_fall_back(self):
        answers = [
            ("bogus", {}),
            ("routine", {"routine": float("nan"), "standard": 0.1, "complex": 0.1}),
            ("routine", {"routine": 1.1, "standard": -0.1, "complex": 0}),
            ("routine", {"routine": 0.9}),
            ("routine", {"routine": 0.9, "standard": 0.9, "complex": 0.9}),
            ("routine", {"routine": 0.1, "standard": 0.8, "complex": 0.1}),
        ]
        for answer in answers:
            with self.subTest(answer=answer):
                result = router.route("task", self.config, "key", lambda *_: answer)
                self.assertEqual(result["route"], "complex")
                self.assertEqual(result["reason"], "jev_unavailable_or_invalid")
                self.assertIsNone(result["classification"])

    def cli(self, task, env=None, config=None):
        args = [
            sys.executable,
            str(ROOT / "scripts/route.py"),
            "--env-file",
            str(ROOT / "absent.env"),
        ]
        if config:
            args.extend(["--config", str(config)])
        return subprocess.run(
            args,
            input=task,
            text=True,
            capture_output=True,
            env={**os.environ, "TYPESAFE_API_KEY": "", **(env or {})},
        )

    def test_missing_key_stops_with_json(self):
        completed = self.cli("Explain a function")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("TYPESAFE_API_KEY", json.loads(completed.stdout)["error"])
        self.assertEqual(completed.stderr, "")

    def test_empty_and_oversized_input_stop(self):
        for task in ("  ", "x" * 12001):
            completed = self.cli(task)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("error", json.loads(completed.stdout))

    def test_missing_config_stops_with_json(self):
        completed = self.cli("task", config=ROOT / "absent.json")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("error", json.loads(completed.stdout))

    def test_invalid_configuration_stops_before_api_call(self):
        invalid = [
            [],
            {**self.config, "routes": ["routine", "standard", "complex"]},
            {**self.config, "routes": {**self.config["routes"], "routine": []}},
            {**self.config, "min_probability": float("nan")},
            {**self.config, "min_probability": True},
            {**self.config, "routes": {}},
            {
                **self.config,
                "routes": {
                    **self.config["routes"],
                    "routine": {"model": "", "reasoning": "low"},
                },
            },
            {
                **self.config,
                "routes": {
                    **self.config["routes"],
                    "routine": {"model": "model", "reasoning": "invented"},
                },
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "models.json"
            for config in invalid:
                with self.subTest(config=config):
                    config_path.write_text(json.dumps(config))
                    completed = self.cli("task", config=config_path)
                    self.assertEqual(completed.returncode, 2)
                    self.assertIn("error", json.loads(completed.stdout))

    def test_explicit_env_file_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("TYPESAFE_API_KEY=file-key\n")
            for existing, expected_key in (
                ({}, "file-key"),
                ({"TYPESAFE_API_KEY": "environment-key"}, "environment-key"),
            ):
                with (
                    self.subTest(existing=existing),
                    patch.dict(os.environ, existing, clear=True),
                    patch.object(
                        sys, "argv", ["route.py", "task", "--env-file", str(env_path)]
                    ),
                    patch.object(router, "route", return_value={"ok": True}) as route,
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    self.assertEqual(router.main(), 0)
                    self.assertEqual(route.call_args.args[2], expected_key)

    def test_main_passes_stdin_to_router_and_prints_json(self):
        output = io.StringIO()
        expected = router.result(self.config, "standard")
        with (
            patch.object(
                sys, "argv", ["route.py", "--env-file", str(ROOT / "absent.env")]
            ),
            patch.object(
                sys, "stdin", io.StringIO("Task with $(shell) and `backticks`")
            ),
            patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-key"}),
            patch.object(router, "route", return_value=expected) as route,
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(router.main(), 0)
        self.assertEqual(json.loads(output.getvalue()), expected)
        self.assertEqual(route.call_args.args[0], "Task with $(shell) and `backticks`")


if __name__ == "__main__":
    unittest.main()
