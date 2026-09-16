# USAGE.md — for agents running promptlab

This file tells an autonomous agent how to run promptlab safely without a
human present to interpret ambiguous output. Read this before invoking any
command.

## Commands

### `promptlab run --suite <file> [--runs N] [--out report.json] [--report]`
Runs every case in a suite against the model and produces a report.

- Use when: you need to know if a prompt currently works, or need a report
  file to feed into `compare` later.
- Do NOT use when: you don't yet have a suite file, or the prompt file the
  suite references doesn't exist — check both exist first, or the command
  will exit 1 or 4 rather than silently skipping.
- Always pass `--out <path>.json` when the result will be read
  programmatically (e.g. by `compare`). Without `--out`, the report prints
  to **stdout** and is still valid JSON — safe to pipe, but not saved to
  disk unless redirected.
- Human-readable status lines always go to **stderr**, never stdout. If you
  are parsing output programmatically, read stdout only; stderr is for a
  human, not for you.

### `promptlab compare --baseline <report.json> --candidate <report.json> [--out diff.json]`
Compares two previously generated reports and classifies every case as
regressed / improved / unchanged / new / removed.

- Use when: you have two reports from the same suite (e.g. before/after
  editing a prompt) and need to know if the change helped.
- Do NOT use when: you only have one report, or the two reports came from
  different suites — the command will still run but will print warnings;
  treat any warning in the output as a reason to double check the inputs
  before trusting the comparison.
- Exit code 2 from this command means at least one case regressed. Do not
  treat exit code 2 as a crash — it is a valid, expected result meaning
  "the candidate is worse in at least one place."

### `promptlab doctor`
Checks that the environment is ready: Python version, model binary
reachable, suite files discoverable, assertion types registered.

- Use when: starting a fresh session, right after cloning the repo, or
  after any error you cannot explain from `run`/`compare` alone — run this
  first to rule out an environment problem before assuming the suite or
  prompt is at fault.
- If `doctor` reports "ISSUES FOUND" (exit code 1), do not proceed to `run`
  or `compare` — fix the reported issue first. Running against a broken
  environment produces misleading results, not just errors.

## Exit codes — what each one means and what to do

| Code | Meaning | What an agent should do |
|---|---|---|
| 0 | Success. All cases passed (`run`) or no regressions (`compare`). | Proceed normally. |
| 1 | Bad usage, or a malformed suite/input file. | Do not retry as-is. Check the command's flags and the suite file's structure against the schema before rerunning. |
| 2 | A result, not a failure: one or more test cases failed (`run`), or a regression was found (`compare`). | Read the `cases`/`failures` section of the output to see exactly what failed, and report it — do not treat this as an unexpected crash. |
| 3 | The model binary could not be invoked (missing, crashed, timed out). | Run `promptlab doctor` first. Do not retry `run` until doctor reports the model as reachable. |
| 4 | A suite or report file was unreadable (missing, wrong permissions, or invalid JSON). | Confirm the file path is correct and the file exists before retrying. |

## Interpreting a `run` report

- `status: "pass"` — every run of every assertion in that case succeeded.
  Trustworthy as-is.
- `status: "fail"` — every run failed. The prompt does not work for this
  case; check `failures` for the specific assertion(s) responsible.
- `status: "flaky"` — some runs passed, some failed (`pass_rate` between 0
  and 1). Do NOT report this case as "working" even if `pass_rate` is high
  (e.g. 0.9) — it is not a pass, and should be reported to the requester as
  inconsistent, not fixed.

## Interpreting a `compare` diff

- A case marked `"regressed"` means it got worse, even if its `pass_rate`
  is still high or its `status` still reads "pass" in the candidate report.
  Always check `baseline_pass_rate` vs `candidate_pass_rate` directly rather
  than relying on the word "pass"/"fail" alone.
- Warnings in the `warnings` field (shared prompt_hash, different suite,
  different model settings) mean the comparison may not be meaningful.
  Surface these warnings to whoever asked for the comparison rather than
  silently proceeding as if the result is trustworthy.

## General rules

- Never modify `stubmodel.py` or call it directly outside of promptlab —
  always go through `promptlab run`, which handles path resolution and
  argument construction correctly.
- Suite file paths (`prompt_file`, file-based `input`) are relative to the
  suite file's own location, not the current working directory. Do not
  assume paths are relative to wherever the command was run from.
- If any command produces a Python traceback instead of one of the exit
  codes above, that is a bug in promptlab itself, not expected behavior —
  do not attempt to work around it by retrying with different flags.