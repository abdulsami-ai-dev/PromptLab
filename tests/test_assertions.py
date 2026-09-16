"""Unit tests for assertions.py"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from assertions import evaluate_assertion, strip_fence, parse_json_output, get_dotted_field


class TestContains(unittest.TestCase):
    def test_contains_pass(self):
        result = {"output": "this is a billing issue"}
        passed, _ = evaluate_assertion({"type": "contains", "value": "billing"}, result)
        self.assertTrue(passed)

    def test_contains_fail(self):
        result = {"output": "this is a billing issue"}
        passed, _ = evaluate_assertion({"type": "contains", "value": "refund"}, result)
        self.assertFalse(passed)

    def test_contains_ignore_case(self):
        result = {"output": "BILLING issue"}
        passed, _ = evaluate_assertion({"type": "contains", "value": "billing", "ignore_case": True}, result)
        self.assertTrue(passed)


class TestJsonValid(unittest.TestCase):
    def test_valid_json_passes(self):
        result = {"output": '{"category": "billing"}'}
        passed, _ = evaluate_assertion({"type": "json_valid"}, result)
        self.assertTrue(passed)

    def test_invalid_json_fails(self):
        result = {"output": "not json at all"}
        passed, _ = evaluate_assertion({"type": "json_valid"}, result)
        self.assertFalse(passed)

    def test_fenced_json_passes(self):
        result = {"output": '```json\n{"category": "billing"}\n```'}
        passed, _ = evaluate_assertion({"type": "json_valid"}, result)
        self.assertTrue(passed)  # per SPEC.md: fenced JSON counts as valid


class TestJsonFieldEquals(unittest.TestCase):
    def test_field_matches(self):
        result = {"output": '{"category": "billing"}'}
        passed, _ = evaluate_assertion(
            {"type": "json_field_equals", "field": "category", "value": "billing"}, result
        )
        self.assertTrue(passed)

    def test_field_mismatch(self):
        result = {"output": '{"category": "technical"}'}
        passed, _ = evaluate_assertion(
            {"type": "json_field_equals", "field": "category", "value": "billing"}, result
        )
        self.assertFalse(passed)

    def test_missing_field(self):
        result = {"output": '{"other": "value"}'}
        passed, _ = evaluate_assertion(
            {"type": "json_field_equals", "field": "category", "value": "billing"}, result
        )
        self.assertFalse(passed)

    def test_nested_field(self):
        result = {"output": '{"meta": {"category": "billing"}}'}
        passed, _ = evaluate_assertion(
            {"type": "json_field_equals", "field": "meta.category", "value": "billing"}, result
        )
        self.assertTrue(passed)


class TestMaxTokens(unittest.TestCase):
    def test_under_limit_passes(self):
        result = {"tokens_out": 10}
        passed, _ = evaluate_assertion({"type": "max_tokens", "value": 40}, result)
        self.assertTrue(passed)

    def test_over_limit_fails(self):
        result = {"tokens_out": 50}
        passed, _ = evaluate_assertion({"type": "max_tokens", "value": 40}, result)
        self.assertFalse(passed)


class TestFinishIs(unittest.TestCase):
    def test_matching_finish_passes(self):
        result = {"finish": "stop"}
        passed, _ = evaluate_assertion({"type": "finish_is", "value": "stop"}, result)
        self.assertTrue(passed)

    def test_mismatched_finish_fails(self):
        result = {"finish": "length"}
        passed, _ = evaluate_assertion({"type": "finish_is", "value": "stop"}, result)
        self.assertFalse(passed)


class TestMatchesRegex(unittest.TestCase):
    def test_regex_match_passes(self):
        result = {"output": "order #12345 confirmed"}
        passed, _ = evaluate_assertion({"type": "matches", "pattern": r"#\d+"}, result)
        self.assertTrue(passed)

    def test_invalid_regex_does_not_crash(self):
        result = {"output": "some text"}
        passed, detail = evaluate_assertion({"type": "matches", "pattern": "[unclosed"}, result)
        self.assertFalse(passed)
        self.assertIn("invalid regex", detail.lower())


class TestStripFence(unittest.TestCase):
    def test_no_fence_unchanged(self):
        self.assertEqual(strip_fence('{"a": 1}'), '{"a": 1}')

    def test_fence_stripped(self):
        self.assertEqual(strip_fence('```json\n{"a": 1}\n```'), '{"a": 1}')


class TestGetDottedField(unittest.TestCase):
    def test_top_level(self):
        self.assertEqual(get_dotted_field({"a": 1}, "a"), 1)

    def test_nested(self):
        self.assertEqual(get_dotted_field({"a": {"b": 2}}, "a.b"), 2)

    def test_missing_raises(self):
        with self.assertRaises(KeyError):
            get_dotted_field({"a": 1}, "b")


if __name__ == "__main__":
    unittest.main()