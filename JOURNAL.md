# JOURNAL.md

## 1. Three decisions we made, and what we rejected in each case

**Flaky policy:** chose strict classification — pass_rate must be exactly
1.0 to count as "pass," anything less (even 0.99) is "flaky" or "fail."
Rejected a percentage threshold (like "90% counts as passing") because it
would need an arbitrary cutoff that's hard to defend, and the brief itself
warns that a case passing 7/10 times is not a passing case.

**Fenced JSON:** chose to treat ```` ``` ````-wrapped JSON as valid,
stripping the fence before parsing. Rejected requiring raw JSON only,
because models commonly wrap output in code fences as a formatting habit
unrelated to whether the actual data is usable.

**Regression definition:** chose zero-tolerance — any pass_rate drop
between baseline and candidate counts as a regression, even something
tiny like 1.0 → 0.95. Rejected a percentage-tolerance threshold for the
same reason as the flaky policy: an arbitrary cutoff invites a question
("why 5% and not 4%?") that's hard to answer convincingly.

## 2. The hardest bug we hit, and how we found the root cause

The first real end-to-end test of `run` failed immediately with
`error: cannot read prompt file: suites\prompts\classify_v1.txt`. At
first glance this looked like a bug in the harness itself. Reading the
error message carefully showed the actual problem: the suite file said
`"prompt_file": "prompts/classify_v1.txt"`, and the code was resolving
that path relative to the suite file's own folder (`suites/`), not the
project root — landing on `suites/prompts/...`, which doesn't exist.
Going back to the brief confirmed this was actually the *correct*,
required behavior ("paths are relative to the suite file, not the
working directory"), not a bug at all. The fix was in the suite file
itself — changing the path to `../prompts/classify_v1.txt` — not in the
code. The lesson: before assuming an error means broken code, check
whether the tool is actually enforcing a rule correctly and the mistake
is somewhere else.

## 3. Something Claude Code got confidently wrong, and how we caught it

Iteration 2 of the prompt (`classify_attempt2.txt`) added the word "JSON"
to the prompt on the prediction that it would at least partially fix the
output-formatting failures. It didn't — 0/8 passed, identical to the
unmodified baseline, confirmed by `compare` showing all 8 cases as
`unchanged`. The assumption that a prompt "sounding more specific" would
change model behavior was wrong; only actually running it through the
harness caught that. This is also the trap the brief warns about directly:
it's easy to assume a plausible-looking prompt change worked without
measuring it.

## 4. What we would do differently with four more hours

Two things stand out. First, time was lost early on waiting for the real
starter files (`stubmodel.py`, `data/tickets.json`) before building
anything — in hindsight, building a temporary stand-in model immediately
and swapping it later cost nothing and should have happened at hour zero,
not after several checkpoints had already passed. Second, the stretch
goals were never attempted (parallel case execution, a result cache,
`--format html`, confidence intervals on pass rate) — with more time,
statistical honesty (a warning when `--runs` is too low to trust a
pass-rate conclusion) would be the first one tackled, since it directly
strengthens the same non-determinism story the whole project is built
around. More edge-case tests matching the hidden-suite categories
(invalid regex, a case truncated mid-JSON by max-tokens, a model refusal)
would also be worth adding before the 21:00 checkpoint, rather than
discovering gaps only when the hidden suites run at judging.

## 5. Who did what — per person

Solo project — one person designed, built, and tested every part of
promptlab: SPEC.md and the 5 required decisions, the CLI (run/compare/
doctor), the 8 assertion types, flaky/pass-rate detection, the report and
compare logic, the unittest suite, and the prompt-improvement iterations
documented in IMPROVEMENT.md.