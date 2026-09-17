# CLAUDE.md — PromptLab Context for Claude Code

## Project Goal

Build promptlab: a Python standard-library CLI harness that runs a suite of test cases
against a prompt via `stubmodel.py`, evaluates assertions, distinguishes pass/fail/flaky
under non-determinism, and reports what changed between two prompt versions.

## Non-Negotiable Requirements

- Python 3.10+, standard library only. No pip installs.
- No network access.
- Invoke the model as a subprocess (`stubmodel.py`). Never import, copy, or reimplement it.
- Preserve the exact CLI contract and exit-code meanings below.
- Support all 8 assertion types.
- Support `--runs N` and flaky classification.
- Reports deterministic apart from isolated timing fields.
- `compare` detects regressions between baseline and candidate reports.
- Never remove existing functionality when adding features.

## CLI Contract

```
promptlab run --suite <file> [--runs N] [--out report.json] [--report]
promptlab compare --baseline <report.json> --candidate <report.json> [--out diff.json]
promptlab doctor
```

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | run: all cases passed / compare: no regression / doctor: all checks OK |
| 1 | bad usage or malformed suite |
| 2 | one or more cases failed (run) / regression found (compare) — a result, not an error |
| 3 | the model could not be invoked |
| 4 | a suite or report file was unreadable |

Never let a traceback reach the user. Missing prompt file, missing input file, missing
model binary, invalid regex, unreadable JSON — each is a one-line message plus the
correct exit code above.

## Suite Format

```json
{
  "name": "classify-smoke",
  "prompt_file": "prompts/classify_v1.txt",
  "model": { "temperature": 0.0, "max_tokens": 256 },
  "runs": 1,
  "cases": [
    {
      "id": "c001",
      "input": "I was charged twice for invoice 7",
      "assert": [
        { "type": "json_valid" },
        { "type": "json_field_equals", "field": "category", "value": "billing" },
        { "type": "not_contains", "value": "Sure" },
        { "type": "max_tokens", "value": 40 },
        { "type": "finish_is", "value": "stop" }
      ]
    }
  ]
}
```

`input` is a string or `{"file": "path"}`, relative to the suite file. `--runs` on the
command line overrides `runs` in the file.

## The 8 Assertion Types (exact semantics)

| Type | Fields | Passes when |
|---|---|---|
| `contains` | `value`, optional `ignore_case` | output contains value |
| `not_contains` | `value`, optional `ignore_case` | it does not |
| `equals` | `value`, optional `normalize` | output equals value (`normalize` strips/collapses whitespace) |
| `matches` | `pattern` | regex finds a match |
| `json_valid` | — | output parses as JSON |
| `json_field_equals` | `field`, `value` | dotted path resolves to that value |
| `max_tokens` | `value` | `tokens_out` at or below value |
| `finish_is` | `value` | `finish` equals `stop`, `length`, or `refusal` |

**Fenced JSON decision (this project's spec):** a ` ```json ` / ` ``` ` fenced block is
stripped before parsing and still counts as valid JSON. `json_field_equals` must use the
same stripped parse — never diverge from `json_valid`'s behavior.

## Report Schema

```json
{
  "suite": "classify-smoke",
  "prompt_file": "prompts/classify_v1.txt",
  "prompt_hash": "a19f40cc21b8",
  "runs": 3,
  "model": { "temperature": 0.4, "max_tokens": 256 },
  "totals": {
    "cases": 20, "passed": 16, "failed": 3, "flaky": 1,
    "tokens_in": 4120, "tokens_out": 980
  },
  "timing": { "wall_ms": 8640 },
  "cases": [
    {
      "id": "c001",
      "status": "pass",
      "pass_rate": 1.0,
      "tokens_out_avg": 21,
      "assertions": [ { "index": 0, "type": "json_valid", "passed": 3, "failed": 0 } ],
      "failures": []
    }
  ]
}
```

`prompt_hash` = first 12 hex chars of SHA-256 of the prompt file's bytes.

**Timing isolation is mandatory:** `wall_ms` lives under a separate top-level `timing` key,
never inside `totals`. Two runs of the same suite at temperature 0 must be byte-identical
except for `timing`. This is checked by a hidden suite — do not regress it.

**Assertion tally must be keyed by (index, type), not type alone.** A case with two
`contains` assertions needs two separate tally entries, each carrying its own `index`, so
the report says which specific assertion is flaky.

## Flaky Policy

- `pass_rate == 1.0` → `status: "pass"`
- `pass_rate == 0.0` → `status: "fail"`
- anything in between → `status: "flaky"`

This is a strict-unanimity policy. It is documented and defended in SPEC.md — do not
change it without updating SPEC.md first.

## Compare Behavior

- Classify every case: `regressed`, `improved`, `unchanged`, `new`, `removed`.
- Any drop in `pass_rate` is a regression, even 1.0 → 0.9 — no silent degradation.
- Report token cost delta (in/out, percent change).
- Warn when baseline and candidate share `prompt_hash`, come from different suites, or
  used different model settings.

## Doctor Checks

Python version, model binary present and responding, suites discoverable in `suites/`,
all 8 assertion types registered. Exit 0 if all OK, 1 if any check fails.

## Development Rules

- Read SPEC.md before implementation changes; update SPEC.md first if a decision changes.
- After any meaningful change, run:
  ```
  python -m unittest discover -s tests
  python promptlab.py run --suite suites/smoke.json --report
  python promptlab.py doctor
  ```
- All paths (model binary, suites dir) resolve relative to the script's own location, not
  the caller's working directory, so the tool works from any invocation directory.

## Prompt Engineering

- Judge prompt changes by promptlab output, not by eyeballing outputs.
- Keep baseline and candidate reports for every change.
- Log each iteration in IMPROVEMENT.md: what changed, predicted effect, measured effect,
  whether it helped. At least 4 iterations, including one that did not help.
- Log key prompting decisions in PROMPTS.md.

## Git Discipline

- First commit contains SPEC.md only — no code.
- `stubmodel.py` is gitignored — graders supply their own binary with the same contract.
- `__pycache__/` is gitignored and untracked.
- SPEC.md must reflect the current design before any code change that departs from it.
