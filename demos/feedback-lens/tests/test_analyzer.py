import copy
import unittest
from unittest.mock import MagicMock, patch

from typesafe_sdk import Choice, Noul, Score, SystemOneResponse

from backend.analyzer import IMPACT, MODEL, analyze, normalize, questions


def response():
    return SystemOneResponse.model_validate(
        {
            "model": MODEL,
            "usage": {"input_tokens": 100, "output_tokens": 10},
            "answers": {
                "theme": {
                    "type": "choice",
                    "choice": "reliability",
                    "confidence": 0.12,
                    "probabilities": {
                        "reliability": 0.8,
                        "usability": 0.1,
                        "capability": 0.05,
                        "pricing": 0.03,
                        "other": 0.02,
                    },
                },
                "actionable": {"type": "noul", "noul": 0.95},
                "impact": {
                    "type": "score",
                    "score": 1.2,
                    "confidence": 0.7,
                    "probabilities": {0: 0.1, 1: 0.6, 2: 0.3},
                    "legend": dict(enumerate(IMPACT)),
                },
            },
        }
    )


class AnalyzerTests(unittest.TestCase):
    def test_three_typed_questions(self):
        q = questions()
        self.assertIsInstance(q["theme"], Choice)
        self.assertIsInstance(q["actionable"], Noul)
        self.assertIsInstance(q["impact"], Score)

    def test_real_adapter_calls_sdk_once_and_preserves_probabilities(self):
        client = MagicMock()
        client.system_one.return_value = response()
        with patch("backend.analyzer.TypeSafeClient") as factory:
            factory.return_value.__enter__.return_value = client
            result = analyze("PDF export is broken.")
        client.system_one.assert_called_once()
        self.assertEqual(
            client.system_one.call_args.kwargs["state"],
            {"feedback": "PDF export is broken."},
        )
        self.assertEqual(len(client.system_one.call_args.kwargs["questions"]), 3)
        self.assertEqual(factory.call_args.kwargs["retry"].max_retries, 0)
        self.assertEqual(factory.call_args.kwargs["timeout"], 30)
        self.assertEqual(result["theme"]["probability"], 0.8)
        self.assertEqual(result["actionable"]["probability"], 0.95)
        self.assertEqual(result["impact"]["score"], 1.2)
        self.assertEqual(result["impact"]["probabilities"], {0: 0.1, 1: 0.6, 2: 0.3})
        self.assertNotIn("confidence", result["theme"])
        self.assertGreaterEqual(result["elapsed_ms"], 0)

    def test_malformed_distributions_fail_closed(self):
        for invalid in [float("nan"), float("inf"), -0.1, 1.1, 0.1, True]:
            with self.subTest(invalid=invalid):
                data = copy.deepcopy(response())
                data.choices["theme"].probabilities["reliability"] = invalid
                with self.assertRaises(ValueError):
                    normalize(data)

    def test_missing_category_and_rubric_mismatch_fail_closed(self):
        data = response()
        del data.choices["theme"].probabilities["other"]
        with self.assertRaises(ValueError):
            normalize(data)
        data = response()
        data.scores["impact"].legend[0] = "A different rubric"
        with self.assertRaises(ValueError):
            normalize(data)

    def test_score_must_agree_with_distribution(self):
        data = response()
        data.scores["impact"].probabilities.update({0: 0.8, 1: 0.1, 2: 0.1})
        with self.assertRaises(ValueError):
            normalize(data)


if __name__ == "__main__":
    unittest.main()
