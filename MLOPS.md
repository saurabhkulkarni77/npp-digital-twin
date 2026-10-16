# MLOps — Level 2 in this repo

This repo runs a Level-2 MLOps setup (CI + CD + CT) adapted to what it
is: a baked static digital twin whose "models" are the three diagnosis
models whose per-step probabilities are baked into
`data/run_<CLASS>.json` — Random Forest (`proba`), Gradient Boosting /
LightGBM (`proba_gbm`), and the soft-voting Ensemble (`proba_ens`).
Training lives in the Task E project workspace; everything that can be
checked, gated, monitored, and released *here* is automated here. The
pattern mirrors the HydroTwin lab repo's Level-2 build.

## Concept map

| Level-2 concept | Implemented as | Where |
|---|---|---|
| CI — code tests | pytest suite on every PR and push to `main`: `app.js` parses as an ES module (node --check), the model toggle in `index.html` offers exactly the three served models with the registry's labels | `.github/workflows/ci.yml`, `tests/test_site_integrity.py` |
| CI — data contracts | manifest (12 classes in canonical order, 17 channels, onset t = 20 s) and every run file: 63 frames on the 0–620 s axis, channel series per frame, RF block = 60 steps of valid 12-class distributions | `tests/test_data_contracts.py` |
| CI — advanced-model contracts | GBM block present at **all 60 steps**; ensemble block present **only** at W = 60/120/300/600 s; both blocks equal the advanced addendum's export snapshot exactly | `tests/test_advanced_probs.py`, `tests/reference_advanced_probs.json` |
| CI — link/asset checks | every relative href/src in `index.html`, importmap target, module import, and data file referenced by `app.js`/manifest resolves to a repo file | `tests/test_links.py` |
| Model registry | versioned registry of all 3 diagnosis models: stage, how each is served in the run files, and its no-oracle test macro-F1 at W = 120/300/600 | `models/registry.json` |
| Validation gate | PRs touching `models/**` fail if a production-stage model's test macro-F1 regresses >1% (relative) vs the frozen baselines at any gated window, unless the PR carries the `allow-regression` label | `models/gate.py`, `models/baselines.json`, `.github/workflows/model-gate.yml` |
| Monitoring | weekly job re-validates run-data integrity + registry consistency from the repo and probes both live hostings (Pages + S3: HTTP 200, toggle present, spot data checks); opens/updates one `mlops-monitor` issue on findings, silent otherwise | `monitor/monitor.py`, `.github/workflows/monitor.yml` |
| Continuous training (CT) | request + validation side here (honest stub); training itself runs in the Task E project workspace (submission notebook + advanced addendum) under the fixed protocol; post-retrain metrics re-enter through the gate | `.github/workflows/retrain.yml`, `retrain/` |
| CD — site deploy | pushes to `main` redeploy GitHub Pages automatically; AWS S3 is synced by the manual deploy workflow in the hydrotwin-site repo (unchanged) | GitHub Pages |
| CD — releases | version tags (or manual dispatch) build the twin distribution ZIP (no `.github/`) and publish a GitHub Release with generated notes | `.github/workflows/release.yml` |

## The gate, in one paragraph

`models/baselines.json` freezes the accepted evaluation — the advanced
addendum's no-oracle test macro-F1 (W = 120/300/600 s: Random Forest
0.964/0.964/0.955, Gradient Boosting 0.963/0.967/0.963, Ensemble
0.967/0.968/0.955). All three models are served by the twin, so all
three are production-stage and gated. A PR that updates
`models/registry.json` with worse numbers fails the gate unless a
maintainer deliberately labels it `allow-regression` — the label
re-runs the gate in warning mode, so the acceptance is visible in the
PR's check history. W = 60 s is deliberately **not** gated: every model
scores ≈ 0.19 there, an information limit of the data, so a 1%
relative band around it would be noise, not signal.

## Monitoring checks

* **Run-data integrity** — per run: 63 frames, manifest channel set,
  RF + GBM rows sum to 1 at all 60 steps, ensemble keys exactly
  {60, 120, 300, 600}.
* **Registry consistency** — registry metrics equal the frozen
  baselines, and every registry model name is a label the page's
  toggle actually serves.
* **Live availability** — GitHub Pages and the AWS S3 endpoint answer
  200 with the model toggle in the served page; the served Pages
  `app.js` names all three models; one AWS run JSON downloads with
  valid probability rows.
* Schedule: Mondays 09:43 UTC, plus manual dispatch. Findings open or
  update a single `mlops-monitor` issue; a clean run is silent (the
  report is still in the run's step summary and artifacts).

## Honest limitations

* The training stage is a validated handoff, not a training run —
  this repo intentionally contains no training code. A "retrain"
  produces new probabilities in the Task E workspace; they are then
  re-baked here and re-gated.
* `tests/reference_advanced_probs.json` is a snapshot of the addendum
  export the current run files were baked from. A deliberate re-bake
  must refresh it in the same PR, or CI fails — by design.
* The monitor's live probes check reachability and key markers, not
  full page rendering; deep UI verification stays with the project's
  browser harness in the Task E workspace.
