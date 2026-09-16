# promptlab — SPEC

promptlab is a CLI tool that runs test cases against a prompt, checks the
output with assertions, and reports whether the prompt actually works —
including when the model is inconsistent across runs.

## Commands
promptlab run --suite <file> [--runs N] [--out report.json] [--report]
promptlab compare --baseline <report.json> --candidate <report.json> [--out diff.json]
promptlab doctor

## Exit codes
0 = all cases passed
1 = bad usage or malformed suite
2 = one or more cases failed
3 = model could not be invoked
4 = suite or report file unreadable

## Assertion Evaluation Model
Decision: all assertions in a case always run, even after one fails.
Reason: the report schema requires per-assertion pass/fail counts for every
assertion type in a case ("assertions": [{"type":..,"passed":N,"failed":N}]).
That's only possible to fill in correctly if every assertion is actually
evaluated every run — stopping early would leave later assertions with no
data. It also means the "failures" field can show everything wrong in one
run instead of needing a rerun after fixing the first issue.
Rejected: stop-on-first-failure. Rejected because it would make per-assertion
stats incomplete, which directly conflicts with the fixed report schema.

## Flaky Policy
Decision: pass_rate == 1.0 → status "pass". pass_rate == 0.0 → status "fail".
Anything strictly between → status "flaky". No middle threshold (e.g. no
"0.8 counts as a pass").
Reason: any arbitrary cutoff (like 80%) has to be justified with a number
that's hard to defend under questioning — "why 80% and not 75%?" A strict
policy needs zero justification for the cutoff itself, and it matches the
brief's own framing: "a case that passes 7 times out of 10 is not a passing
case." It also behaves sanely at low --runs counts (1/2 passes is obviously
not a clean pass, and this policy correctly flags it as flaky rather than
needing a special rule for small N).
Rejected: percentage threshold (e.g. ≥90% = pass). Rejected because it hides
real inconsistency behind a number that's ultimately arbitrary, and the
brief explicitly warns against a tool that "lies" about flaky cases.

## Fenced JSON
Decision: JSON wrapped in a ```` ``` ```` code fence counts as valid — strip
the fence (and any language tag like "json") before parsing.
Reason: models very commonly wrap JSON in fences as a formatting habit; a
prompt is meant to be judged on whether the *data* it returns is usable, not
on cosmetic wrapping. Being lenient here means a prompt isn't penalized for
something the model does regardless of instructions.
Consistency: json_field_equals uses the exact same fence-stripping step
before parsing, so both assertion types agree on what counts as JSON.
Rejected: raw JSON only (fenced = invalid). Rejected because it would
conflate two different problems — "is the data structurally valid" vs "did
the model add markdown formatting" — into one assertion.

## Regression Definition
Decision: any decrease in a case's pass_rate between baseline and candidate,
no matter how small (> 0), counts as a regression.
Reason: the brief itself confirms a drop from 1.0 to 0.9 must count as a
regression ("silent degradation is exactly what this tool exists to catch").
A zero-tolerance rule needs no extra justification for a threshold and
guarantees that exact example is caught. A softer rule (e.g. "only flag
drops over 5%") would have to explain why 0.1 is over the line but 0.04 gets
ignored — a harder position to defend live.
Rejected: percentage-tolerance threshold. Rejected for the same reason as the
flaky threshold — an arbitrary cutoff invites a question you don't want to
be asked twice.

## Cost Accounting
Decision: per-case numbers (tokens_out_avg) are averages across that case's
runs. The top-level "totals" block is a sum across all cases and all runs.
Reason: this is mostly dictated by the schema itself — the field is literally
named tokens_out_avg at the case level, and wall_ms at the totals level only
makes sense as an actual elapsed total, not an average. Compare's cost delta
(percentage change) is computed on the totals, since that reflects real
cost impact of switching prompts, not a per-case abstraction.

## Failure Taxonomy
- Malformed suite (missing field / wrong type / unknown assertion type) → exit 1
- Suite references a prompt or input file that doesn't exist → exit 1
- Model binary missing or fails to start → exit 3
- Invalid regex in a `matches` assertion → treated as that assertion failing, case continues, reason recorded in `failures`
- Malformed / unreadable report passed to compare → exit 4
- One or more test cases failed after a clean run → exit 2

## Definition of Done
- All 8 assertion types implemented with the semantics above
- --runs N works and produces correct pass/fail/flaky classification
- Report output matches the fixed schema exactly, byte-identical at temp 0
  across repeated runs (excluding timing fields)
- No uncaught exception/traceback under any error condition in the hidden-suite categories
- compare correctly classifies regressed/improved/unchanged/new/removed and warns on incomparable reports
- doctor checks Python version, model reachability, suite discoverability, assertion registry
- python -m unittest passes from a fresh clone
- Every decision above can be explained out loud without looking at this file