#!/usr/bin/env python3
"""promptlab - a test runner for prompts."""

import argparse
import sys


def cmd_run(args):
    print(f"[run] suite={args.suite} runs={args.runs}", file=sys.stderr)
    # TODO: real logic comes in Step 3
    return 0


def cmd_compare(args):
    print(f"[compare] baseline={args.baseline} candidate={args.candidate}", file=sys.stderr)
    # TODO: real logic comes later
    return 0


def cmd_doctor(args):
    print("[doctor] checking environment...", file=sys.stderr)
    # TODO: real logic comes later
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