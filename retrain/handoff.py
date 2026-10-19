#!/usr/bin/env python3
"""Continuous-training handoff validator (honest stub).

Model training does NOT run in this repo. The twin's diagnosis model
(the Random Forest) is trained and evaluated in the Task E project
workspace (submission notebook), under the project's fixed protocol:
split by run (train 725 / val 242 / test 244), 88 no-oracle channels,
windows W = 60/120/300/600 s, macro-F1.

This script validates a retrain request against models/registry.json
and prints the handoff summary: which model(s), and the exact
downstream steps. It never trains anything and never claims to.

Usage: python retrain/handoff.py --model all|rf|gbm|ens --reason "..."
"""
import argparse
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True,
                    help="registry key (see models/registry.json) or 'all'")
    ap.add_argument("--reason", default="manual")
    args = ap.parse_args()

    registry = json.loads((ROOT / "models" / "registry.json")
                          .read_text(encoding="utf-8"))
    by_key = {m["key"]: m for m in registry["models"]}
    if args.model != "all" and args.model not in by_key:
        print(f"::error::unknown model {args.model!r}; known keys: "
              f"{sorted(by_key)} (or 'all')")
        return 1

    models = list(by_key.values()) if args.model == "all" \
        else [by_key[args.model]]
    names = ", ".join(f"{m['name']} ({m['key']})" for m in models)
    summary = f"""## CT handoff — retrain request validated

- **Models:** {names}
- **Reason:** {args.reason}
- **Requested from:** npp-digital-twin (this repo)
- **Protocol (fixed):** Task E — split by run (725/242/244), 88
  no-oracle channels, windows W = 60/120/300/600 s, test macro-F1.

### Where training actually runs
The Task E project workspace: the submission notebook (the Random
Forest and the homework's other models). This workflow is the
*request + validation* side of continuous training only; it does not
train models itself.

### Downstream steps after a retrain completes there
1. Export the Random Forest's per-step probabilities for the twin's
   12 baked runs (all 60 steps).
2. Re-bake `data/run_<CLASS>.json` with the new export.
3. Update `models/registry.json` in a PR with the new test macro-F1 —
   the **model validation gate** (`.github/workflows/model-gate.yml`)
   must pass: no production-stage model may regress >1% vs
   `models/baselines.json` without the `allow-regression` label
   (deliberate baseline updates re-freeze baselines in the same PR).
4. CI (`tests/`) must pass before the Pages/S3 deployments are
   considered good.
"""
    print(summary)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
