# PROMPTS.md — 5 key prompts from building promptlab

## 1. Understanding the brief
**Asked:** Explain the hackathon brief and guide me step by step — what
actually needs to be built.
**Got back:** A full technical breakdown (commands, assertion types,
report schema, the 5 required decisions).
**Changed:** The first explanation used too much jargon. Asked for a
plain-English version instead — the real one that stuck was the "in one
line" version without terms like "schema" or "subprocess" assumed.
**Why:** Understanding the actual requirements correctly, before writing
SPEC.md, mattered more than getting to code fast — a misunderstood
requirement here would have cascaded into every later step.

## 2. Writing SPEC.md with real reasoning
**Asked:** Write the complete SPEC.md, including reasoning for the 5
required decisions (flaky policy, fenced JSON, regression threshold,
assertion evaluation order, cost accounting) — not just the answers.
**Got back:** Full SPEC.md with a documented decision + rejected
alternative for each of the 5 choices.
**Changed:** Nothing structurally — but flagged that the "Understanding"
score depends on being able to defend these live, so each decision was
read and understood before committing, not just pasted in.
**Why:** These 5 decisions are graded as reasoning, not fact — the wrong
move here is copying without being able to explain "why not the other
option" at the viva.

## 3. Wiring the model call into `run` — a real bug found by testing
**Asked:** Connect the assertion logic and the model call into the `run`
command for real.
**Got back:** A working version — but the first actual test run failed
with `error: cannot read prompt file: suites\prompts\classify_v1.txt`.
**Changed:** The suite file's `prompt_file` path was wrong — it needed
`../prompts/classify_v1.txt`, not `prompts/classify_v1.txt`, because paths
are relative to the suite file's own location, not the project root (a
rule stated explicitly in the brief). Fixed the suite file, re-tested,
confirmed exit code 0.
**Why:** This wasn't a code bug — the harness was actually enforcing the
"paths relative to suite file" rule correctly. It caught our own mistake
in writing the suite file, exactly the kind of thing hidden test suites
are designed to check.

## 4. Proving flaky detection actually works, not just in theory
**Asked:** Add `--runs N` and flaky/pass-rate classification.
**Got back:** Working code — but the first two test runs both showed
`pass_rate=0.00` (a consistent fail), not flaky, because the placeholder
prompt caused the same assertion (`not_contains "Sure"`) to fail every
single run with no chance of passing.
**Changed:** Rewrote the placeholder prompt to trigger the model's clean-
JSON mode, and raised temperature to 0.7, specifically to create a case
that could plausibly pass sometimes and fail other times. Re-ran with
`--runs 10` and got `FLAKY (pass_rate=0.80)` with per-assertion counts
showing exactly which assertion caused it.
**Why:** A flaky classifier that's never actually seen a flaky case is
unproven. Deliberately engineering a flaky scenario was the only way to
confirm MUST 10-13 (the core non-determinism requirement) genuinely works.

## 5. Building `compare` and confirming regression detection with a real diff
**Asked:** Build the `compare` command per SPEC.md's regression definition
(any pass_rate drop counts, even a small one).
**Got back:** Working code — tested by generating a real baseline report,
deliberately weakening the prompt, generating a candidate report, then
comparing them.
**Changed:** Nothing needed fixing — the first real test correctly showed
`[REGRESSED] c001: 1.00 -> 0.00` plus the token cost delta. Kept as-is.
**Why:** This is the one entry that confirms something worked correctly
the first time it was tested against real data, not just in isolated unit
tests — worth recording as evidence the comparison logic matches the spec.