# MLOps — Level 2 in this repo

This repo runs a Level-2 MLOps setup (CI + CD + CT) adapted to what it
is: a baked static digital twin whose "model" is the diagnosis model
whose per-step probabilities are baked into `data/run_<CLASS>.json` —
the Random Forest (`proba`), the classical baseline of Task E item E2.
(Gradient Boosting / LightGBM and a soft-voting RF + GBM + TCN ensemble
from the post-homework advanced addendum were also baked in briefly;
they were removed on 2026-10-19 when the twin was aligned to the
homework's model list — see the note at the end of this file.)
Training lives in the Task E project workspace; everything that can be
checked, gated, monitored, and released *here* is automated here. The
pattern mirrors the HydroTwin lab repo's Level-2 build.

## Concept map

| Level-2 concept | Implemented as | Where |
|---|---|---|
| CI — code tests | pytest suite on every PR and push to `main`: `app.js` parses as an ES module (node --check), `index.html` presents exactly the one served model with the registry's label | `.github/workflows/ci.yml`, `tests/test_site_integrity.py` |
| CI — data contracts | manifest (12 classes in canonical order, 17 channels, onset t = 20 s) and every run file: 63 frames on the 0–620 s axis, channel series per frame, RF block = 60 steps of valid 12-class distributions | `tests/test_data_contracts.py` |
| CI — link/asset checks | every relative href/src in `index.html`, importmap target, module import, and data file referenced by `app.js`/manifest resolves to a repo file | `tests/test_links.py` |
| Model registry | versioned registry of the diagnosis model: stage, how it is served in the run files, and its no-oracle test macro-F1 at W = 120/300/600 | `models/registry.json` |
| Validation gate | PRs touching `models/**` fail if a production-stage model's test macro-F1 regresses >1% (relative) vs the frozen baselines at any gated window, unless the PR carries the `allow-regression` label | `models/gate.py`, `models/baselines.json`, `.github/workflows/model-gate.yml` |
| Monitoring | weekly job re-validates run-data integrity + registry consistency from the repo and probes both live hostings (Pages + S3: HTTP 200, model tag present, spot data checks); opens/updates one `mlops-monitor` issue on findings, silent otherwise | `monitor/monitor.py`, `.github/workflows/monitor.yml` |
| Continuous training (CT) | request + validation side here (honest stub); training itself runs in the Task E project workspace (submission notebook) under the fixed protocol; post-retrain metrics re-enter through the gate | `.github/workflows/retrain.yml`, `retrain/` |
| CD — site deploy | pushes to `main` redeploy GitHub Pages automatically; AWS S3 is synced by the manual deploy workflow in the hydrotwin-site repo (unchanged) | GitHub Pages |
| CD — releases | version tags (or manual dispatch) build the twin distribution ZIP (no `.github/`) and publish a GitHub Release with generated notes | `.github/workflows/release.yml` |

## The gate, in one paragraph

`models/baselines.json` freezes the accepted evaluation — the no-oracle
test macro-F1 (W = 120/300/600 s: Random Forest 0.964/0.964/0.955).
The forest is the twin's only served model, so it is production-stage
and gated. A PR that updates
`models/registry.json` with worse numbers fails the gate unless a
maintainer deliberately labels it `allow-regression` — the label
re-runs the gate in warning mode, so the acceptance is visible in the
PR's check history. W = 60 s is deliberately **not** gated: every model
scores ≈ 0.19 there, an information limit of the data, so a 1%
relative band around it would be noise, not signal.

## Monitoring checks

* **Run-data integrity** — per run: 63 frames, manifest channel set,
  RF rows sum to 1 at all 60 steps.
* **Registry consistency** — registry metrics equal the frozen
  baselines, and the registry model name is a label the page
  actually serves.
* **Live availability** — GitHub Pages and the AWS S3 endpoint answer
  200 with the diagnosis-model tag in the served page; the served Pages
  `app.js` names the registry model; one AWS run JSON downloads with
  valid probability rows.
* Schedule: Mondays 09:43 UTC, plus manual dispatch. Findings open or
  update a single `mlops-monitor` issue; a clean run is silent (the
  report is still in the run's step summary and artifacts).

## Honest limitations

* The training stage is a validated handoff, not a training run —
  this repo intentionally contains no training code. A "retrain"
  produces new probabilities in the Task E workspace; they are then
  re-baked here and re-gated.
* Until 2026-10-19 the twin also served the advanced addendum's
  Gradient Boosting and Ensemble models; their baked blocks
  (`proba_gbm`, `proba_ens`) and the snapshot test
  (`tests/reference_advanced_probs.json`) were removed with the models
  when the twin was aligned to the homework's model list (Task E:
  logistic regression / random forest, 1D CNN, LSTM / GRU).
* The round-2 split-conformal prediction sets (`conf` blocks in the
  run files plus the chips UI) were removed on 2026-10-19, when all
  advanced modeling was dropped from Homework 2; the twin serves the
  core homework diagnosis only. A regression test
  (`tests/test_conformal_regression.py`) keeps `conf` out of the
  baked runs and the page.
* The monitor's live probes check reachability and key markers, not
  full page rendering; deep UI verification stays with the project's
  browser harness in the Task E workspace.
