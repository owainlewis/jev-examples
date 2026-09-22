import importlib.util
import io
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "classify", Path(__file__).parents[1] / "scripts/classify.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ReadinessTests(unittest.TestCase):
    def test_decisions(self):
        for values, label in [
            ((0.9, 0.9, 0.1), "agent-ready"),
            ((0.8, 0.8, 0.2), "agent-ready"),
            ((0.1, 0.9, 0.1), "needs-clarification"),
            ((0.9, 0.9, 0.8), "needs-clarification"),
            ((0.6, 0.9, 0.1), "needs-review"),
            ((0.5, 0.1, 0.5), "needs-clarification"),
        ]:
            with self.subTest(values=values):
                self.assertEqual(m.decide(dict(zip(m.CHECKS, values)))["label"], label)

    def test_invalid_probabilities(self):
        for value in [float("nan"), float("inf"), -1, 2, True, "0.9"]:
            with self.assertRaises(ValueError):
                m.decide(dict(zip(m.CHECKS, [value, 0.9, 0.1])))
        with self.assertRaises(ValueError):
            m.decide({})

    def test_input_boundaries(self):
        for issue in [
            {"title": ""},
            {"title": "x", "state": "closed"},
            {"title": "x", "pull_request": {}},
            {"title": "x", "body": "a" * 24000},
        ]:
            with self.assertRaises(ValueError):
                m.validate_issue(issue)
        for url in [
            "https://github.com/a/b/pull/1",
            "https://evil.com/a/b/issues/1",
            "https://github.com/a/b/issues/1;echo",
        ]:
            with self.assertRaises(ValueError):
                m.issue_path(url)
        self.assertEqual(
            m.issue_path("https://github.com/a/b/issues/1"), "repos/a/b/issues/1"
        )

    def test_labels_preserve_unrelated_and_rerun(self):
        issue = {
            "title": "x",
            "body": "y",
            "state": "open",
            "updated_at": "now",
            "labels": [{"name": "bug"}, {"name": "needs-review"}],
        }
        original = dict(issue)
        writes = []

        def api(path, *args, payload=None):
            if "?" in path:
                return [{"name": name} for name in m.LABELS]
            if args:
                writes.append((path, args, payload))
                if args[-1] == "POST":
                    for name in payload["labels"]:
                        if {"name": name} not in issue["labels"]:
                            issue["labels"].append({"name": name})
                else:
                    issue["labels"] = [
                        i for i in issue["labels"] if i["name"] != path.split("/")[-1]
                    ]
                return None
            return issue

        m.apply_label("repos/a/b/issues/1", original, "agent-ready", api)
        m.apply_label("repos/a/b/issues/1", original, "agent-ready", api)
        self.assertEqual({i["name"] for i in issue["labels"]}, {"bug", "agent-ready"})
        self.assertFalse(any("bug" in path for path, _, _ in writes))

    def test_api_failure_never_applies_labels(self):
        with (
            patch.object(
                m.sys,
                "argv",
                ["classify", "--issue", "https://github.com/a/b/issues/1", "--apply"],
            ),
            patch.dict(m.os.environ, {"TYPESAFE_API_KEY": "test"}),
            patch.object(m, "gh", return_value={"title": "x", "body": "y"}),
            patch.object(m, "classify", side_effect=RuntimeError("secret")),
            patch.object(m, "apply_label") as apply,
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            self.assertEqual(m.main(), 1)
            apply.assert_not_called()
            self.assertNotIn("secret", output.getvalue())
            self.assertIn("GitHub was not changed", output.getvalue())

    def test_preview_never_applies_labels(self):
        with (
            patch.object(
                m.sys,
                "argv",
                ["classify", "--issue", "https://github.com/a/b/issues/1"],
            ),
            patch.dict(m.os.environ, {"TYPESAFE_API_KEY": "test"}),
            patch.object(m, "gh", return_value={"title": "x", "body": "y"}),
            patch.object(m, "classify", return_value={"label": "agent-ready"}),
            patch.object(m, "apply_label") as apply,
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            self.assertEqual(m.main(), 0)
            apply.assert_not_called()
            self.assertIn('"applied": false', output.getvalue())

    def test_changed_issue_prevents_writes(self):
        def api(path, *args, **kwargs):
            self.assertFalse(args)
            return {"title": "changed"}

        with self.assertRaises(ValueError):
            m.apply_label("repos/a/b/issues/1", {"title": "old"}, "agent-ready", api)


if __name__ == "__main__":
    unittest.main()
