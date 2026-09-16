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
            "wall_ms": wall_ms,
        },
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
    print(f"tokens_in: {t['tokens_in']}  tokens_out: {t['tokens_out']}  wall_ms: {t['wall_ms']}", file=sys.stderr)

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