#!/usr/bin/env python3
"""Model validation gate for the NPP digital twin registry.

Compares models/registry.json against the frozen models/baselines.json.

Fails (exit 1) when:
  * the registry's model set differs from the baselines' model set,
  * the registry's gated windows differ from the baselines' windows,
  * any production-stage model's no-oracle test macro-F1 at a gated
    window (W = 120/300/600 s) regresses by more than the registry's
    tolerance (default 1% relative) versus its baseline. Macro-F1 is a
    higher-is-better metric, so a regression means the registry value
    dropped below baseline * (1 - tolerance).

A regression can be accepted deliberately by passing --allow-regression
(the `allow-regression` PR label; see .github/workflows/model-gate.yml),
which downgrades regressions to warnings. Structural problems always fail.

Usage: python models/gate.py [--allow-regression]
"""
import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def load(name):
    with open(HERE / name, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-regression", action="store_true",
                    help="accept production-metric regressions (PR label override)")
    args = ap.parse_args()

    registry = load("registry.json")
    baselines = load("baselines.json")
    problems = []

    reg_models = {m["name"]: m for m in registry["models"]}
    base_names = set(baselines["test_macro_f1"])
    if set(reg_models) != base_names:
        problems.append(
            f"model set mismatch: registry={sorted(reg_models)} "
            f"baselines={sorted(base_names)}")

    gated = [str(w) for w in baselines["dataset"]["gated_windows_s"]]
    reg_windows = [str(w) for w in registry["dataset"]["windows_s"]]
    missing = [w for w in gated if w not in reg_windows]
    if missing:
        problems.append(
            f"gated windows {missing} not present in registry windows "
            f"{reg_windows}")

    tol = float(registry.get("gate", {}).get("tolerance_rel", 0.01))
    regressions = []
    for name, model in sorted(reg_models.items()):
        if model.get("stage") != "production":
            continue
        base_table = baselines["test_macro_f1"].get(name, {})
        for w in gated:
            base = base_table.get(w)
            cur = model.get("test_macro_f1", {}).get(w)
            if base is None or cur is None:
                problems.append(f"{name}: missing test_macro_f1 at W={w} "
                                "(registry or baseline)")
                continue
            if not (0.0 < cur <= 1.0):
                problems.append(f"{name}: implausible test_macro_f1 {cur} "
                                f"at W={w}")
                continue
            rel = (cur - base) / base
            status = "ok"
            if rel < -tol:
                status = "REGRESSION"
                regressions.append(
                    f"{name} W={w}: {cur} vs baseline {base} "
                    f"({rel:+.2%} < -tolerance {tol:.0%})")
            print(f"gate: {name:28s} W={w:>3s}  {cur:.3f} vs {base:.3f} "
                  f"({rel:+.2%}) {status}")

    for p in problems:
        print(f"::error::gate: {p}")

    if regressions:
        for r in regressions:
            if args.allow_regression:
                print(f"::warning::gate: regression accepted via override: {r}")
            else:
                print(f"::error::gate: {r}")
        if not args.allow_regression:
            print("gate: FAIL — production metric regression without the "
                  "'allow-regression' label")
            return 1

    if problems:
        print("gate: FAIL — structural problems above")
        return 1

    print("gate: PASS"
          + (" (with accepted regressions)" if regressions else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
