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