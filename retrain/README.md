# CT — retrain handoff (honest stub)

`handoff.py` validates a retrain request for one (or all) of the
twin's diagnosis models against `models/registry.json` and prints the
handoff summary. Trigger it from **Actions → "CT — retrain handoff
(stub)" → Run workflow**.

It deliberately does **not** train anything. Training and evaluation
live in the Task E project workspace (submission notebook +
advanced-modeling addendum) under the fixed Task E protocol: split by
run (train 725 / validation 242 / test 244), 88 no-oracle channels,
windows W = 60/120/300/600 s, test macro-F1. After a retrain there,
the new probabilities are exported and re-baked into
`data/run_<CLASS>.json`, `tests/reference_advanced_probs.json` is
refreshed, and the new metrics re-enter this repo through a
`models/registry.json` PR guarded by the validation gate — see
`MLOPS.md`.
