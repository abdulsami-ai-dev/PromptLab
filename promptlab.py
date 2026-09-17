#!/usr/bin/env python3
"""promptlab - a test runner for prompts."""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from assertions import evaluate_assertion


def resolve_input(input_value, suite_dir):
    if isinstance(input_value, dict):
        return "@" + str(suite_dir / input_value["file"])
    return input_value


def call_model(prompt_file, input_arg, temperature, max_tokens):
    cmd = [
        sys.executable, "stubmodel.py",
        "--prompt", str(prompt_file),
        "--input", input_arg,
        "--temperature", str(temperature),
        "--max-tokens", str(max_tokens),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, result.stderr.strip()
    try:
        model_result = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        return None, f"model output was not valid JSON: {e}"
    return model_result, None


def hash_prompt_file(prompt_file):
    with open(prompt_file, "rb") as f:
        content = f.read()
    return hashlib.sha256(content).hexdigest()[:12]


VALID_ASSERTION_TYPES = {
    "contains": ["value"],
    "not_contains": ["value"],
    "equals": ["value"],
    "matches": ["pattern"],
    "json_valid": [],
    "json_field_equals": ["field", "value"],
    "max_tokens": ["value"],
    "finish_is": ["value"],
}


def validate_suite(suite):
    """Returns None if the suite is valid, or a readable error string."""
    if not isinstance(suite, dict):
        return "suite must be a JSON object"

    if "prompt_file" not in suite:
        return "missing required field: prompt_file"
    if not isinstance(suite["prompt_file"], str):
        return "prompt_file must be a string"

    if "cases" not in suite:
        return "missing required field: cases"
    if not isinstance(suite["cases"], list):
        return "cases must be a list"

    if "model" in suite and not isinstance(suite["model"], dict):
        return "model must be an object"

    if "runs" in suite and not isinstance(suite["runs"], int):
        return "runs must be an integer"

    seen_ids = set()
    for i, case in enumerate(suite["cases"]):
        if not isinstance(case, dict):
            return f"case at index {i} must be an object"

        if "id" not in case:
            return f"case at index {i} missing required field: id"
        case_id = case["id"]
        if case_id in seen_ids:
            return f"duplicate case id: {case_id}"
        seen_ids.add(case_id)

        if "input" not in case:
            return f"case '{case_id}' missing required field: input"
        input_val = case["input"]
        if not isinstance(input_val, (str, dict)):
            return f"case '{case_id}': input must be a string or a {{'file': ...}} object"
        if isinstance(input_val, dict) and "file" not in input_val:
            return f"case '{case_id}': input object must contain a 'file' field"

        assertions_list = case.get("assert", [])
        if not isinstance(assertions_list, list):
            return f"case '{case_id}': assert must be a list"

        for j, a in enumerate(assertions_list):
            if not isinstance(a, dict):
                return f"case '{case_id}', assertion {j}: must be an object"
            if "type" not in a:
                return f"case '{case_id}', assertion {j}: missing 'type'"
            a_type = a["type"]
            if a_type not in VALID_ASSERTION_TYPES:
                return f"case '{case_id}': unknown assertion type '{a_type}'"
            for required_field in VALID_ASSERTION_TYPES[a_type]:
                if required_field not in a:
                    return f"case '{case_id}': assertion '{a_type}' missing required field '{required_field}'"

    return None


def run_case(case, prompt_file, model_cfg, suite_dir, num_runs):
    input_arg = resolve_input(case["input"], suite_dir)
    temperature = model_cfg.get("temperature", 0.0)
    max_tokens = model_cfg.get("max_tokens", 256)
    assertions_list = case.get("assert", [])

    run_outcomes = []
    assertion_tally = {}
    all_failures = []
    tokens_out_values = []
    tokens_in_total = 0

    for run_index in range(num_runs):
        model_result, error = call_model(prompt_file, input_arg, temperature, max_tokens)

        if error:
            run_outcomes.append(False)
            all_failures.append({"run": run_index, "type": "model_error", "detail": error})
            continue

        tokens_out_values.append(model_result.get("tokens_out", 0))
        tokens_in_total += model_result.get("tokens_in", 0)

        this_run_passed = True
        for assertion in assertions_list:
            passed, detail = evaluate_assertion(assertion, model_result)
            a_type = assertion["type"]
            tally = assertion_tally.setdefault(a_type, {"passed": 0, "failed": 0})
            if passed:
                tally["passed"] += 1
            else:
                tally["failed"] += 1
                this_run_passed = False
                all_failures.append({
                    "run": run_index,
                    "type": a_type,
                    "detail": detail,
                    "output": model_result.get("output", "")[:200],
                })

        run_outcomes.append(this_run_passed)

    pass_rate = sum(run_outcomes) / len(run_outcomes) if run_outcomes else 0.0
    if pass_rate == 1.0:
        status = "pass"
    elif pass_rate == 0.0:
        status = "fail"
    else:
        status = "flaky"

    tokens_out_avg = sum(tokens_out_values) / len(tokens_out_values) if tokens_out_values else 0

    return {
        "id": case["id"],
        "status": status,
        "pass_rate": pass_rate,
        "tokens_out_avg": round(tokens_out_avg, 2),
        "tokens_in_total": tokens_in_total,
        "assertions": [
            {"type": a_type, "passed": tally["passed"], "failed": tally["failed"]}
            for a_type, tally in assertion_tally.items()
        ],
        "failures": all_failures,
    }


def build_report(suite, suite_path, prompt_file, num_runs, case_results, wall_ms):
    total_cases = len(case_results)
    passed = sum(1 for c in case_results if c["status"] == "pass")
    failed = sum(1 for c in case_results if c["status"] == "fail")
    flaky = sum(1 for c in case_results if c["status"] == "flaky")
    tokens_in = sum(c["tokens_in_total"] for c in case_results)
    tokens_out = sum(round(c["tokens_out_avg"] * num_runs) for c in case_results)

    return {
        "suite": suite.get("name", ""),
        "prompt_file": suite["prompt_file"],
        "prompt_hash": hash_prompt_file(prompt_file),
        "runs": num_runs,
        "model": suite.get("model", {}),
        "totals": {
            "cases": total_cases,
            "passed": passed,
            "failed": failed,
            "flaky": flaky,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        },
        "timing": {"wall_ms": wall_ms},
        "cases": [
            {
                "id": c["id"],
                "status": c["status"],
                "pass_rate": c["pass_rate"],
                "tokens_out_avg": c["tokens_out_avg"],
                "assertions": c["assertions"],
                "failures": c["failures"],
            }
            for c in case_results
        ],
    }


def print_human_summary(report):
    t = report["totals"]
    print(f"\n=== {report['suite']} ===", file=sys.stderr)
    print(f"cases: {t['cases']}  passed: {t['passed']}  failed: {t['failed']}  flaky: {t['flaky']}", file=sys.stderr)
    print(f"tokens_in: {t['tokens_in']}  tokens_out: {t['tokens_out']}  wall_ms: {report['timing']['wall_ms']}", file=sys.stderr)

    worst = [c for c in report["cases"] if c["status"] != "pass"]
    worst.sort(key=lambda c: c["pass_rate"])
    if worst:
        print("worst offenders:", file=sys.stderr)
        for c in worst[:5]:
            print(f"  [{c['status'].upper()}] {c['id']} (pass_rate={c['pass_rate']:.2f})", file=sys.stderr)


def cmd_run(args):
    suite_path = Path(args.suite)

    try:
        with open(suite_path, "r", encoding="utf-8") as f:
            suite = json.load(f)
    except OSError:
        print(f"error: cannot read suite file: {suite_path}", file=sys.stderr)
        return 4
    except json.JSONDecodeError as e:
        print(f"error: suite file is not valid JSON: {e}", file=sys.stderr)
        return 1

    validation_error = validate_suite(suite)
    if validation_error:
        print(f"error: malformed suite: {validation_error}", file=sys.stderr)
        return 1

    suite_dir = suite_path.parent
    prompt_file = suite_dir / suite["prompt_file"]
    model_cfg = suite.get("model", {})
    num_runs = args.runs if args.runs is not None else suite.get("runs", 1)

    if not prompt_file.exists():
        print(f"error: prompt file not found: {prompt_file}", file=sys.stderr)
        return 1

    start_time = time.time()
    case_results = [
        run_case(case, prompt_file, model_cfg, suite_dir, num_runs)
        for case in suite.get("cases", [])
    ]
    wall_ms = int((time.time() - start_time) * 1000)

    report = build_report(suite, suite_path, prompt_file, num_runs, case_results, wall_ms)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    else:
        print(json.dumps(report, indent=2))

    if args.report:
        print_human_summary(report)

    any_failed = any(c["status"] != "pass" for c in case_results)
    return 2 if any_failed else 0


def load_report(path, label):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        print(f"error: cannot read {label} report: {path}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"error: {label} report is not valid JSON: {e}", file=sys.stderr)
        return None


def build_comparison(baseline, candidate):
    warnings = []
    if baseline.get("prompt_hash") == candidate.get("prompt_hash"):
        warnings.append("baseline and candidate share the same prompt_hash — comparing a prompt against itself")
    if baseline.get("suite") != candidate.get("suite"):
        warnings.append(f"different suites: baseline='{baseline.get('suite')}' candidate='{candidate.get('suite')}'")
    if baseline.get("model") != candidate.get("model"):
        warnings.append(f"different model settings: baseline={baseline.get('model')} candidate={candidate.get('model')}")

    baseline_cases = {c["id"]: c for c in baseline.get("cases", [])}
    candidate_cases = {c["id"]: c for c in candidate.get("cases", [])}
    all_ids = set(baseline_cases) | set(candidate_cases)

    case_diffs = []
    for case_id in sorted(all_ids):
        b = baseline_cases.get(case_id)
        c = candidate_cases.get(case_id)

        if b and not c:
            case_diffs.append({"id": case_id, "classification": "removed"})
            continue
        if c and not b:
            case_diffs.append({"id": case_id, "classification": "new"})
            continue

        b_rate, c_rate = b["pass_rate"], c["pass_rate"]
        if c_rate > b_rate:
            classification = "improved"
        elif c_rate < b_rate:
            classification = "regressed"
        else:
            classification = "unchanged"

        case_diffs.append({
            "id": case_id,
            "classification": classification,
            "baseline_pass_rate": b_rate,
            "candidate_pass_rate": c_rate,
        })

    b_totals = baseline.get("totals", {})
    c_totals = candidate.get("totals", {})

    def pct_change(old, new):
        return None if old == 0 else round(((new - old) / old) * 100, 2)

    cost_delta = {
        "tokens_in_baseline": b_totals.get("tokens_in", 0),
        "tokens_in_candidate": c_totals.get("tokens_in", 0),
        "tokens_in_pct_change": pct_change(b_totals.get("tokens_in", 0), c_totals.get("tokens_in", 0)),
        "tokens_out_baseline": b_totals.get("tokens_out", 0),
        "tokens_out_candidate": c_totals.get("tokens_out", 0),
        "tokens_out_pct_change": pct_change(b_totals.get("tokens_out", 0), c_totals.get("tokens_out", 0)),
    }

    return {"warnings": warnings, "cost_delta": cost_delta, "cases": case_diffs}


def print_comparison_summary(diff):
    if diff["warnings"]:
        print("WARNINGS:", file=sys.stderr)
        for w in diff["warnings"]:
            print(f"  - {w}", file=sys.stderr)

    counts = {}
    for c in diff["cases"]:
        counts[c["classification"]] = counts.get(c["classification"], 0) + 1
    print(f"cases: {counts}", file=sys.stderr)

    for c in diff["cases"]:
        if c["classification"] in ("regressed", "improved"):
            print(f"  [{c['classification'].upper()}] {c['id']}: {c['baseline_pass_rate']:.2f} -> {c['candidate_pass_rate']:.2f}", file=sys.stderr)

    cd = diff["cost_delta"]
    print(f"tokens_in: {cd['tokens_in_baseline']} -> {cd['tokens_in_candidate']} ({cd['tokens_in_pct_change']}%)", file=sys.stderr)
    print(f"tokens_out: {cd['tokens_out_baseline']} -> {cd['tokens_out_candidate']} ({cd['tokens_out_pct_change']}%)", file=sys.stderr)


def cmd_compare(args):
    baseline = load_report(args.baseline, "baseline")
    if baseline is None:
        return 4
    candidate = load_report(args.candidate, "candidate")
    if candidate is None:
        return 4

    diff = build_comparison(baseline, candidate)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(diff, f, indent=2)
    else:
        print(json.dumps(diff, indent=2))

    print_comparison_summary(diff)

    has_regression = any(c["classification"] == "regressed" for c in diff["cases"])
    return 2 if has_regression else 0


def cmd_doctor(args):
    ok = True
    print("promptlab doctor", file=sys.stderr)

    print(f"Python version: {sys.version.split()[0]}", file=sys.stderr)
    if sys.version_info < (3, 10):
        print("  WARNING: Python 3.10+ required", file=sys.stderr)
        ok = False
    else:
        print("  OK", file=sys.stderr)

    model_path = Path("stubmodel.py")
    if not model_path.exists():
        print(f"Model binary: NOT FOUND at {model_path}", file=sys.stderr)
        ok = False
    else:
        try:
            result = subprocess.run(
                [sys.executable, str(model_path), "--prompt", "SPEC.md", "--input", "doctor check"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                print("Model binary: reachable and responding", file=sys.stderr)
            else:
                print(f"Model binary: responded with exit code {result.returncode}", file=sys.stderr)
                ok = False
        except Exception as e:
            print(f"Model binary: failed to invoke ({e})", file=sys.stderr)
            ok = False

    suites_dir = Path("suites")
    if suites_dir.exists():
        suite_files = list(suites_dir.glob("*.json"))
        print(f"Suites discoverable: {len(suite_files)} found in {suites_dir}/", file=sys.stderr)
        for sf in suite_files:
            print(f"  - {sf}", file=sys.stderr)
    else:
        print(f"Suites: directory {suites_dir}/ not found", file=sys.stderr)
        ok = False

    known_assertions = ["contains", "not_contains", "equals", "matches",
                         "json_valid", "json_field_equals", "max_tokens", "finish_is"]
    print(f"Assertion types registered: {len(known_assertions)}", file=sys.stderr)
    for a in known_assertions:
        print(f"  - {a}", file=sys.stderr)

    print("doctor: " + ("ALL OK" if ok else "ISSUES FOUND"), file=sys.stderr)
    return 0 if ok else 1


def build_parser():
    parser = argparse.ArgumentParser(prog="promptlab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_p = subparsers.add_parser("run")
    run_p.add_argument("--suite", required=True)
    run_p.add_argument("--runs", type=int, default=None)
    run_p.add_argument("--out")
    run_p.add_argument("--report", action="store_true")
    run_p.set_defaults(func=cmd_run)

    compare_p = subparsers.add_parser("compare")
    compare_p.add_argument("--baseline", required=True)
    compare_p.add_argument("--candidate", required=True)
    compare_p.add_argument("--out")
    compare_p.set_defaults(func=cmd_compare)

    doctor_p = subparsers.add_parser("doctor")
    doctor_p.set_defaults(func=cmd_doctor)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    exit_code = args.func(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()