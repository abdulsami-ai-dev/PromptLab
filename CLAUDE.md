# CLAUDE.md — context for AI assistance on this repo

## What this project is
promptlab: a stdlib-only Python CLI that runs test cases against a prompt,
checks the model's output with assertions, and reports whether the prompt
works — including correctly handling non-deterministic model output across
repeated runs.

## Hard constraints — do not violate these regardless of what seems cleaner
- Python standard library only. No pip installs, no third-party packages,
  ever — not even for something that would obviously be easier with one.
- Never `import` or reimplement `stubmodel.py`'s logic. It must always be
  invoked as a subprocess via `subprocess.run([...])`. The judged binary
  will be swapped for a different one with the same CLI contract; any code
  that assumes something about *what* the model says (rather than just the
  contract it guarantees) is wrong.
- The report JSON schema (suite, prompt_file, prompt_hash, runs, model,
  totals, cases[]) is fixed by the brief. Do not rename fields, change
  nesting, or add/remove top-level keys without updating SPEC.md first.
- Exit codes are fixed: 0 pass, 1 bad usage/malformed suite, 2 case(s)
  failed or comparison found a regression, 3 model unreachable, 4 file
  unreadable. Exit code 2 is a valid result, not an error path — never
  treat it as something to "fix" by swallowing it.
- No uncaught exception should ever reach the user. Every file-read,
  JSON-parse, and subprocess call is wrapped and converted into the right
  exit code and a one-line message.
- Human-readable text always goes to stderr. Report/diff JSON goes to
  stdout (or --out). Never mix the two.

## Decisions already made in SPEC.md — do not silently change these
- Assertion evaluation: ALL assertions in a case run every time, even after
  one fails (needed for per-assertion pass/fail counts in the report).
- Flaky policy: strict — pass_rate == 1.0 is "pass", == 0.0 is "fail",
  anything in between is "flaky". No percentage threshold.
- Fenced JSON (```` ``` ````-wrapped) counts as valid JSON for both
  `json_valid` and `json_field_equals` — strip the fence before parsing.
- Regression definition: ANY pass_rate decrease between baseline and
  candidate counts as regressed, even something like 1.0 → 0.95.
- Cost accounting: per-case `tokens_out_avg` is an average across that
  case's runs; the top-level `totals` block is a sum across all cases/runs.

If asked to change any of the above, update SPEC.md first, then the code —
never the other way around.

## File layout
- `promptlab.py` — the CLI: argument parsing, run/compare/doctor commands,
  report building.
- `assertions.py` — the 8 assertion types, evaluated independently of the
  CLI so it can be unit-tested on its own.
- `stubmodel.py` — the model binary (temporary dev stand-in until the real
  one is provided; gitignored, never treated as project code).
- `suites/` — test suite JSON files.
- `prompts/` — prompt text files referenced by suites.
- `tests/` — unittest coverage for assertions.py and promptlab.py logic
  (not for prompts — that's IMPROVEMENT.md's job).

## Working style used on this project
- Spec-first: SPEC.md was written and committed alone, before any code,
  per the brief's process requirement.
- Every change was built and manually verified in the terminal (paste real
  output back) before being accepted, rather than assumed to be correct
  because it looked plausible.
- Each git commit represents one working, tested increment (skeleton →
  assertions/flaky → report schema → compare → doctor → tests), not a
  single large dump of code.