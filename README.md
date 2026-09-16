# promptlab

A CLI test runner for LLM prompts — runs test cases against a prompt,
checks assertions on the output, and correctly distinguishes pass / fail /
flaky when the model's output isn't fully deterministic.

## Requirements
- Python 3.10+
- Standard library only — no `pip install` needed

## Quick start (fresh clone → working demo)

```powershell
# 1. Check the environment is ready
python promptlab.py doctor

# 2. Run the smoke suite
python promptlab.py run --suite suites/smoke.json --report

# 3. Run the full evaluation suite, save a report
python promptlab.py run --suite suites/classify_eval_v2.json --out report.json --report

# 4. Compare two reports (baseline vs improved prompt)
python promptlab.py compare --baseline baseline_v1.json --candidate candidate_v2.json

# 5. Run the unit tests
python -m unittest discover -s tests
```

## Commands

- `promptlab run --suite <file> [--runs N] [--out report.json] [--report]`
  — runs every case in a suite, N times each, reports pass/fail/flaky.
- `promptlab compare --baseline <report.json> --candidate <report.json> [--out diff.json]`
  — diffs two reports, flags regressions even on small pass-rate drops.
- `promptlab doctor` — checks Python version, model binary, suite
  discovery, and assertion registry.

## Project structure


## Documentation

- `SPEC.md` — the 5 required design decisions and reasoning, written
  before any code (first commit).
- `IMPROVEMENT.md` — baseline → 4 iterations → final prompt, with real
  measured results from this harness.
- `USAGE.md` — agent-facing docs (what each exit code means, when to use
  each command).
- `CLAUDE.md` / `PROMPTS.md` — how AI assistance was used on this project.
- `JOURNAL.md` — five-question reflection.

## Note on `stubmodel.py`

The real starter-provided model binary was not received in time to build
against from hour zero, so a temporary stand-in (same CLI contract: same
flags, same JSON output shape, deterministic at temperature 0, random
above it) was used to build and test the harness. It's excluded from git
via `.gitignore`. **The real `stubmodel.py` must be dropped into this same
location before final judging** — no other code changes are needed, since
`promptlab.py` only ever calls it as a subprocess and never assumes
anything about what it says beyond the documented CLI contract.