# NPP Digital Twin — NPPAD Accident Diagnosis (Task E)

A WebXR-style digital twin of a PCTRAN pressurized-water reactor, built for the
Task E take-home project (*Predicting the Boiling Crisis*, NPPAD accident
diagnosis). Pick one of 12 simulated accidents and watch the plant respond in
3D while the project's diagnosis model identifies the accident live, from the
sensor channels alone.

## Run it

Fully self-contained and offline (Three.js is vendored; no CDN, no build step).
Serve the folder with any static server — opening `index.html` via `file://`
will not work because the run data is loaded with `fetch`:

```bash
cd npp_digital_twin
python3 -m http.server 8000
# open http://localhost:8000
```

Also hosted at:
- GitHub Pages: https://saurabhkulkarni77.github.io/npp-digital-twin/
- AWS S3: http://npp-digital-twin-2026.s3-website-us-east-1.amazonaws.com
  (bucket `npp-digital-twin-2026`, us-east-1, static website hosting).
  Deployed via the manual **"Deploy NPP Digital Twin to AWS S3"** workflow in
  the `hydrotwin-site` repo (Actions → Run workflow), which uses that repo's
  AWS secrets to create/configure the bucket and sync this repo's site files.
  The included `.github/workflows/deploy-aws.yml` mirrors the same deploy for
  anyone who forks this repo and adds their own AWS secrets.

## What you see

- **3D plant** — reactor vessel with a glowing core and moving control rods,
  pressurizer, two steam-generator loops with pumps, steam and feedwater lines,
  turbine hall, translucent containment. Water levels in the pressurizer and
  steam generators, core heat, rod position, and a flashing break marker are
  all driven frame-by-frame by the simulated channel data (each run's
  deviation from its own steady state) — not by canned animation.
- **Live diagnosis panel** — top-3 accident probabilities from the
  **Random Forest** (the classical baseline of Task E item E2), updated as
  the observation window W grows, with its **90% conformal prediction
  set**: the classes the forest cannot rule out at 90% coverage
  (split-conformal, calibrated per step on validation runs).
  Probabilities stay near-uniform at W ≤ 60 s and sharpen after ~120 s —
  the project's core finding, visible live. A *Reveal true accident*
  toggle scores the model.
- **Channel charts** — any 6 of 17 key channels (RCS pressure, pressurizer
  level, SG levels/pressures, steam/feed flows, temperatures, power, DNBR,
  void fraction, cladding temperature), cursor synced to playback, with the
  t = 20 s accident-injection line marked.
- **Playback** — play/pause, 0.5–4× speed, scrub bar (red tick = injection).
- **VR** — an *Enter VR* button appears on WebXR-capable browsers (same
  pattern as the HydroTwin station pages); desktop mouse orbit works everywhere.

## The runs

One held-out **test** run per accident class — the median-severity run among
the class's full-length test runs, under the notebook's run-level split:

| Class | Run file | Severity | | Class | Run file | Severity |
|---|---|---|---|---|---|---|
| LOCA  | LOCA/51.csv  | 51 | | RW    | RW/51.csv    | 51 |
| LOCAC | LOCAC/51.csv | 51 | | RI    | RI/-40.csv   | -40 |
| SLBIC | SLBIC/51.csv | 51 | | FLB   | FLB/51.csv   | 51 |
| SLBOC | SLBOC/51.csv | 51 | | MD    | MD/51.csv    | 51 |
| SGATR | SGATR/51.csv | 51 | | LR    | LR/51.csv    | 51 |
| SGBTR | SGBTR/56.csv | 56 | | LLB   | LLB/51.csv   | 51 |

Each run is baked for t = 0–620 s at the native 10 s sampling (63 frames):
17 chart channels plus the diagnosis probabilities for every 10 s step.

## The model (provenance — read this before quoting numbers)

The original Task E run saved metrics, not model files, so the forest here was
**retrained with the notebook's exact protocol**: same run-level split (within
class, sorted by severity, k mod 5 → test/val/train), the 88 realistic
*no-oracle* channels, the notebook's `summary_features` (last value, mean,
slope per channel), `RandomForestClassifier(n_estimators=400,
class_weight="balanced_subsample", random_state=2026)`. One instance was
trained per 10 s step k = 1…60 (window = first k samples from t = 20 s) so the
panel can update continuously; the notebook itself evaluated W = 30/60/120/300/600 s.

Validation — retrained vs notebook test macro-F1 (no-oracle random forest):

| W | Retrained | Notebook |
|---|---|---|
| 30 s  | 0.1924 | 0.1877 |
| 60 s  | 0.1917 | 0.1877 |
| 120 s | 0.9635 | 0.9635 |
| 300 s | 0.9642 | 0.9642 |
| 600 s | 0.9554 | 0.9554 |

Exact agreement at W ≥ 120 s; the W ≤ 60 s regime is near-chance for every
model, where the fourth decimal is seed jitter.

### Only the homework's models are served

The twin serves the assignment's own diagnosis model for the panel — the
Random Forest above. Gradient Boosting (LightGBM) and a soft-voting
RF + GBM + TCN ensemble from the post-homework advanced-modeling addendum
were served here briefly and removed on 2026-10-19, when the twin was
aligned to the model list named in the assignment (Task E: logistic
regression / random forest, 1D CNN, LSTM / GRU). The addendum's results
stand in the project files, not in this twin.

## Honest quirks of the data

- **SLBOC barely moves the plant in the first 600 s** — at every severity, no
  physical channel deviates more than ~0.05 % in the window (PCTRAN's
  outside-containment break develops over the full ~5,500 s run). Its break
  marker therefore stays dim; the forest still identifies the class from small
  systematic deviations across the 88 channels.
- **LOCA/51 is already separable at W = 30 s** (a mid-size break moves the
  pressurizer fast); most other classes are not. Both behaviours are the
  model's real outputs on these runs.
- The simulator channel `RBLK` ramps identically across unrelated runs (an
  elapsed-bookkeeping artifact, not plant physics) and is deliberately unused.

## Layout

```
index.html  styles.css  app.js     the app (Three.js scene + UI + charts)
vendor/                            three.module.js (r160, MIT) + OrbitControls.js
data/manifest.json                 classes, channel metadata, run index, model card
data/run_<CLASS>.json              one baked test run per class (channels + per-step
                                   probabilities: proba = RF at all 60 steps, plus the
                                   forest's 90% conformal sets in conf)
.github/workflows/deploy-aws.yml   optional AWS S3 deploy (mirrors HydroTwin)
```

Data: NPPAD (PCTRAN simulations), https://github.com/thu-inet/NuclearPowerPlantAccidentData.
Built as a companion visualization for the Task E submission; it does not
change any submitted deliverable.

## MLOps (Level 2)

This repo runs a Level-2 MLOps setup around the twin's baked Random
Forest diagnosis model — CI tests for the site, the run data, and the
conformal prediction sets; a versioned model registry with a
validation gate (no served model's test macro-F1 may regress >1% vs
the frozen baselines without an `allow-regression` label); a weekly
monitor that re-validates the baked data and probes both live
hostings, filing a single `mlops-monitor` issue on findings; an honest
continuous-training handoff stub (training itself lives in the Task E
project workspace); and versioned GitHub Releases carrying the twin
distribution ZIP. Full concept → implementation map: [MLOPS.md](MLOPS.md).
