"""Assertion evaluation for promptlab — the 8 required assertion types."""

import json
import re


def strip_fence(text):
    """Removes a ```/```json code fence if present (SPEC.md decision:
    fenced JSON still counts as valid)."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def parse_json_output(output):
    cleaned = strip_fence(output)
    return json.loads(cleaned)


def get_dotted_field(data, path):
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError(f"field '{path}' not found")
    return current


def normalize_whitespace(text):
    return " ".join(text.split())


def evaluate_assertion(assertion, model_result):
    """Returns (passed: bool, detail: str)."""
    a_type = assertion["type"]
    output = model_result.get("output", "")

    if a_type == "contains":
        value = assertion["value"]
        haystack = output.lower() if assertion.get("ignore_case") else output
        needle = value.lower() if assertion.get("ignore_case") else value
        return needle in haystack, f"expected output to contain {value!r}"

    if a_type == "not_contains":
        value = assertion["value"]
        haystack = output.lower() if assertion.get("ignore_case") else output
        needle = value.lower() if assertion.get("ignore_case") else value
        return needle not in haystack, f"expected output to NOT contain {value!r}"

    if a_type == "equals":
        value = assertion["value"]
        if assertion.get("normalize"):
            passed = normalize_whitespace(output) == normalize_whitespace(value)
        else:
            passed = output == value
        return passed, f"expected output to equal {value!r}"

    if a_type == "matches":
        pattern = assertion["pattern"]
        try:
            return re.search(pattern, output) is not None, f"expected match for pattern {pattern!r}"
        except re.error as e:
            return False, f"invalid regex {pattern!r}: {e}"

    if a_type == "json_valid":
        try:
            parse_json_output(output)
            return True, "output is valid JSON"
        except json.JSONDecodeError as e:
            return False, f"output is not valid JSON: {e}"

    if a_type == "json_field_equals":
        field = assertion["field"]
        expected = assertion["value"]
        try:
            data = parse_json_output(output)
            actual = get_dotted_field(data, field)
            return actual == expected, f"expected field '{field}' == {expected!r}, got {actual!r}"
        except json.JSONDecodeError as e:
            return False, f"output is not valid JSON: {e}"
        except KeyError as e:
            return False, str(e)

    if a_type == "max_tokens":
        limit = assertion["value"]
        actual = model_result.get("tokens_out", 0)
        return actual <= limit, f"expected tokens_out <= {limit}, got {actual}"

    if a_type == "finish_is":
        expected = assertion["value"]
        actual = model_result.get("finish")
        return actual == expected, f"expected finish == {expected!r}, got {actual!r}"

    return False, f"unknown assertion type: {a_type}"


if __name__ == "__main__":
    # Manual self-check only — the real graded tests go in tests/ later.
    fake_result = {"output": '{"category": "billing"}', "tokens_out": 6, "finish": "stop"}
    checks = [
        ({"type": "contains", "value": "billing"}, True),
        ({"type": "not_contains", "value": "Sure"}, True),
        ({"type": "json_valid"}, True),
        ({"type": "json_field_equals", "field": "category", "value": "billing"}, True),
        ({"type": "max_tokens", "value": 40}, True),
        ({"type": "finish_is", "value": "stop"}, True),
        ({"type": "finish_is", "value": "length"}, False),
    ]
    for assertion, expected in checks:
        passed, detail = evaluate_assertion(assertion, fake_result)
        status = "OK" if passed == expected else "MISMATCH"
        print(f"[{status}] {assertion['type']}: passed={passed} ({detail})")