#!/usr/bin/env python3
"""
TEMPORARY stand-in for the real stubmodel.py.
Follows the same CLI contract from the brief so promptlab.py can be built
and tested. DELETE this and drop in the real stubmodel.py before doing any
real prompt-improvement work or final submission.
"""

import argparse
import json
import math
import random
import sys
import time


def read_input(value):
    if value.startswith("@"):
        with open(value[1:], "r", encoding="utf-8") as f:
            return f.read()
    return value


def count_tokens(text):
    return math.ceil(len(text) / 4) if text else 0


def fake_response(prompt_text, input_text):
    text = input_text.lower()
    if any(w in text for w in ["charge", "invoice", "refund", "billing", "payment"]):
        category = "billing"
    elif any(w in text for w in ["error", "bug", "crash", "broken", "not working"]):
        category = "technical"
    elif any(w in text for w in ["cancel", "account", "password", "login"]):
        category = "account"
    else:
        category = "general"

    strict = "json" in prompt_text.lower() and "only" in prompt_text.lower()
    if strict:
        return json.dumps({"category": category}), "stop"
    return (
        f'Sure! I think this is a {category} issue.\n{{"category": "{category}"}}',
        "stop",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--call-index", type=int, default=0)
    args = parser.parse_args()

    try:
        with open(args.prompt, "r", encoding="utf-8") as f:
            prompt_text = f.read()
    except OSError:
        print(f"error: cannot read prompt file: {args.prompt}", file=sys.stderr)
        sys.exit(3)

    try:
        input_text = read_input(args.input)
    except OSError:
        print(f"error: cannot read input file: {args.input}", file=sys.stderr)
        sys.exit(3)

    start = time.time()
    output, finish = fake_response(prompt_text, input_text)

    if args.temperature > 0.0:
        rng = random.Random(args.seed + args.call_index) if args.seed is not None else random.Random()
        wobble = rng.random()
        if wobble < 0.3:
            output = output.replace('"category"', '"CATEGORY"')
        elif wobble < 0.5:
            output = "```json\n" + output + "\n```"

    tokens_in = count_tokens(prompt_text) + count_tokens(input_text)
    tokens_out = count_tokens(output)

    if tokens_out > args.max_tokens:
        output = output[: args.max_tokens * 4]
        tokens_out = count_tokens(output)
        finish = "length"

    latency_ms = int((time.time() - start) * 1000) + 5

    print(json.dumps({
        "output": output,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "finish": finish,
        "latency_ms": latency_ms,
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()