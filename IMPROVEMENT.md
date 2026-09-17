# IMPROVEMENT.md

⚠️ **Important caveat:** everything below was measured using a temporary
stand-in `stubmodel.py` and placeholder ticket data, because the real
starter files (`stubmodel.py`, `data/tickets.json`) were not provided at
kickoff. **This entire loop must be re-run against the real model and real
ticket corpus before submission** — see "Redoing this with real data" at
the bottom. What this document proves right now is that the *measurement
process itself* works correctly and was used honestly, iteration by
iteration.

## Baseline — `prompts/classify_v1.txt`

Deliberately weak prompt, no output-format instruction:


Result (`baseline_v1.json`, suite `classify_eval.json`, 8 cases, temperature 0.0):
- 0/8 passed, 8/8 failed, 0 flaky
- tokens_in: 306, tokens_out: 130
- Every case failed the same way: model prefixed its answer with
  "Sure! I think this is a ___ issue." — breaking both `not_contains "Sure"`
  and `json_valid`, since the output wasn't pure JSON.

## Iteration 2 — `prompts/classify_attempt2.txt` (the one that didn't help)

Change made:

**Prediction:** mentioning "JSON" would at least partially fix the
`json_valid` failures, even if the "Sure!" preamble stuck around.

**Actual result** (`attempt2.json`, compared to baseline):
- 0/8 passed — identical to baseline, `compare` classified all 8 cases as
  `unchanged`
- tokens_in: 274 (-10.46%), tokens_out: 130 (0.0%) — no real change

**Was the prediction right? No.** Just mentioning the word "JSON" without
an explicit "only"/"no other text" instruction did nothing — the model
still added its usual preamble. This is the core lesson of the whole
exercise: a prompt "sounding" more specific doesn't mean it behaves
differently, and eyeballing the wording instead of running it through the
harness would have missed this completely.

## Iteration 3 — `prompts/classify_attempt3.txt`

Change made:

**Prediction:** adding "only" alongside "JSON" should trigger clean,
prefix-free output and fix most failures — but since the prompt doesn't
name the exact category options or the exact field name, some cases might
still fail on `json_field_equals`.

**Actual result** (`attempt3.json`, compared to baseline):
- 8/8 passed — all 8 cases `IMPROVED` (0.00 → 1.00 pass_rate)
- tokens_in: 290 (-5.23%), tokens_out: 50 (-61.54%)

**Was the prediction right? Partially.** The "only" instruction alone was
enough to fully fix every case — the concern about `json_field_equals`
failing on unnamed categories turned out not to happen on this test set.
Good reminder that predictions should be checked against real runs, not
assumed correct just because they sound cautious.

## Iteration 4 — `prompts/classify_v2.txt` (final)

Change made — added the explicit category list and exact output format on
top of attempt 3: