#!/usr/bin/env python3
"""promptlab - a test runner for prompts."""

import argparse
import json
import subprocess
import sys
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


def run_case(case, prompt_file, model_cfg, suite_dir, num_runs):
    input_arg = resolve_input(case["input"], suite_dir)
    temperature = model_cfg.get("temperature", 0.0)
    max_tokens = model_cfg.get("max_tokens", 256)
    assertions_list = case.get("assert", [])

    run_outcomes = []       # True/False per run (did the whole case pass that run)
    assertion_tally = {}    # type -> {"passed": N, "failed": N}
    all_failures = []       # debug info for any failed assertion, any run

    for run_index in range(num_runs):
        model_result, error = call_model(prompt_file, input_arg, temperature, max_tokens)

        if error:
            run_outcomes.append(False)
            all_failures.append({"run": run_index, "type": "model_error", "detail": error})
            continue

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

    return {
        "id": case["id"],
        "status": status,
        "pass_rate": pass_rate,
        "assertion_tally": assertion_tally,
        "failures": all_failures,
    }


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

    suite_dir = suite_path.parent
    prompt_file = suite_dir / suite["prompt_file"]
    model_cfg = suite.get("model", {})
    num_runs = args.runs if args.runs is not None else suite.get("runs", 1)

    any_failed = False
    for case in suite.get("cases", []):
        result = run_case(case, prompt_file, model_cfg, suite_dir, num_runs)

        if result["status"] != "pass":
            any_failed = True

        print(f"[{result['id']}] {result['status'].upper()} (pass_rate={result['pass_rate']:.2f}, runs={num_runs})", file=sys.stderr)
        for a_type, tally in result["assertion_tally"].items():
            print(f"    {a_type}: passed={tally['passed']} failed={tally['failed']}", file=sys.stderr)
        for failure in result["failures"][:3]:
            print(f"    [run {failure['run']}] {failure['type']}: {failure.get('detail', '')}", file=sys.stderr)

    return 2 if any_failed else 0


def cmd_compare(args):
    print(f"[compare] baseline={args.baseline} candidate={args.candidate}", file=sys.stderr)
    return 0


def cmd_doctor(args):
    print("[doctor] checking environment...", file=sys.stderr)
    return 0


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