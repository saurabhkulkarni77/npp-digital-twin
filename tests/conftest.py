"""Shared fixtures/constants for the NPP digital twin CI test suite.

The suite validates the *baked* twin exactly as it is served: page/JS
sanity, run-data contracts (12 runs x 63 frames x 60 diagnosis steps),
the advanced-model probability blocks against the Task E addendum
reference snapshot, and internal asset/link targets. Everything is
stdlib-only apart from pytest itself.
"""
import json
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Canonical class order (data/manifest.json `classes`; probability rows
# in every run file follow this order).
CLASSES = [
    "LOCA", "LOCAC", "SLBIC", "SLBOC", "SGATR", "SGBTR",
    "RW", "RI", "FLB", "MD", "LR", "LLB",
]

# The 17 sensor channels charted by the twin (manifest `channels`).
N_CHANNELS = 17

# Time axis: 63 frames at t = 0..620 s in 10 s steps; accident onset at
# t = 20 s; diagnosis steps k = 1..60 (diagnosis at t = 20 + 10k s).
N_FRAMES = 63
N_STEPS = 60
T_ONSET = 20.0

# Windows (seconds of post-onset data) at which the ensemble exists.
ENSEMBLE_W = ["60", "120", "300", "600"]

# Probability rows are baked rounded to 4 dp, so a 12-class row can sum
# to 1 +/- ~0.001; 0.01 is a safe contract tolerance.
SUM_TOL = 0.01


@pytest.fixture(scope="session")
def repo_root():
    return REPO_ROOT


@pytest.fixture(scope="session")
def manifest(repo_root):
    with open(repo_root / "data" / "manifest.json", encoding="utf-8") as f:
        return json.load(f)


def load_run(repo_root, cls):
    with open(repo_root / "data" / f"run_{cls}.json", encoding="utf-8") as f:
        return json.load(f)
