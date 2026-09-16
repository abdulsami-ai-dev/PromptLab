"""Unit tests for promptlab.py's own logic (not assertions.py)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from promptlab import build_comparison, resolve_input


class TestResolveInput(unittest.TestCase):
    def test_plain_string_passthrough(self):
        result = resolve_input("hello world", Path("suites"))
        self.assertEqual(result, "hello world")

    def test_file_reference_becomes_at_path(self):
        result = resolve_input({"file": "data/case1.txt"}, Path("suites"))
        self.assertTrue(result.startswith("@"))
        self.assertIn("case1.txt", result)


class TestBuildComparisonClassification(unittest.TestCase):
    def make_report(self, prompt_hash, suite_name, model, cases):
        return {
            "prompt_hash": prompt_hash,
            "suite": suite_name,
            "model": model,
            "totals": {"tokens_in": 100, "tokens_out": 50},
            "cases": cases,
        }

    def test_improved_case(self):
        baseline = self.make_report("aaa", "s1", {"temperature": 0.0}, [
            {"id": "c1", "pass_rate": 0.5}
        ])
        candidate = self.make_report("bbb", "s1", {"temperature": 0.0}, [
            {"id": "c1", "pass_rate": 1.0}
        ])
        diff = build_comparison(baseline, candidate)
        self.assertEqual(diff["cases"][0]["classification"], "improved")

    def test_regressed_case_even_small_drop(self):
        baseline = self.make_report("aaa", "s1", {"temperature": 0.0}, [
            {"id": "c1", "pass_rate": 1.0}
        ])
        candidate = self.make_report("bbb", "s1", {"temperature": 0.0}, [
            {"id": "c1", "pass_rate": 0.95}
        ])
        diff = build_comparison(baseline, candidate)
        # per SPEC.md: ANY drop counts as regression, even a small one
        self.assertEqual(diff["cases"][0]["classification"], "regressed")

    def test_unchanged_case(self):
        baseline = self.make_report("aaa", "s1", {"temperature": 0.0}, [
            {"id": "c1", "pass_rate": 1.0}
        ])
        candidate = self.make_report("bbb", "s1", {"temperature": 0.0}, [
            {"id": "c1", "pass_rate": 1.0}
        ])
        diff = build_comparison(baseline, candidate)
        self.assertEqual(diff["cases"][0]["classification"], "unchanged")

    def test_new_case(self):
        baseline = self.make_report("aaa", "s1", {"temperature": 0.0}, [])
        candidate = self.make_report("bbb", "s1", {"temperature": 0.0}, [
            {"id": "c1", "pass_rate": 1.0}
        ])
        diff = build_comparison(baseline, candidate)
        self.assertEqual(diff["cases"][0]["classification"], "new")

    def test_removed_case(self):
        baseline = self.make_report("aaa", "s1", {"temperature": 0.0}, [
            {"id": "c1", "pass_rate": 1.0}
        ])
        candidate = self.make_report("bbb", "s1", {"temperature": 0.0}, [])
        diff = build_comparison(baseline, candidate)
        self.assertEqual(diff["cases"][0]["classification"], "removed")


class TestBuildComparisonWarnings(unittest.TestCase):
    def make_report(self, prompt_hash, suite_name, model):
        return {
            "prompt_hash": prompt_hash, "suite": suite_name, "model": model,
            "totals": {"tokens_in": 100, "tokens_out": 50}, "cases": [],
        }

    def test_same_prompt_hash_warns(self):
        baseline = self.make_report("same_hash", "s1", {"temperature": 0.0})
        candidate = self.make_report("same_hash", "s1", {"temperature": 0.0})
        diff = build_comparison(baseline, candidate)
        self.assertTrue(any("prompt_hash" in w for w in diff["warnings"]))

    def test_different_suite_warns(self):
        baseline = self.make_report("aaa", "suite-one", {"temperature": 0.0})
        candidate = self.make_report("bbb", "suite-two", {"temperature": 0.0})
        diff = build_comparison(baseline, candidate)
        self.assertTrue(any("suite" in w for w in diff["warnings"]))

    def test_different_model_settings_warns(self):
        baseline = self.make_report("aaa", "s1", {"temperature": 0.0})
        candidate = self.make_report("bbb", "s1", {"temperature": 0.7})
        diff = build_comparison(baseline, candidate)
        self.assertTrue(any("model" in w for w in diff["warnings"]))

    def test_no_warnings_for_clean_comparison(self):
        baseline = self.make_report("aaa", "s1", {"temperature": 0.0})
        candidate = self.make_report("bbb", "s1", {"temperature": 0.0})
        diff = build_comparison(baseline, candidate)
        self.assertEqual(diff["warnings"], [])


class TestCostDelta(unittest.TestCase):
    def test_token_percentage_calculated(self):
        baseline = {
            "prompt_hash": "aaa", "suite": "s1", "model": {},
            "totals": {"tokens_in": 100, "tokens_out": 50}, "cases": [],
        }
        candidate = {
            "prompt_hash": "bbb", "suite": "s1", "model": {},
            "totals": {"tokens_in": 150, "tokens_out": 100}, "cases": [],
        }
        diff = build_comparison(baseline, candidate)
        self.assertEqual(diff["cost_delta"]["tokens_in_pct_change"], 50.0)
        self.assertEqual(diff["cost_delta"]["tokens_out_pct_change"], 100.0)


if __name__ == "__main__":
    unittest.main()