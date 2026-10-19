"""Contracts for the round-2 twin additions (Task E advanced round 2).

- Every baked run carries a `conf` block of 90% LAC split-conformal
  prediction sets: per-step sets for RF and GBM (60 steps) and ensemble
  sets at the four gated windows W in {60, 120, 300, 600} s. A LAC set
  built from a probability row always contains that row's argmax class.
- data/explain.json carries the per-class top-8 sensor lists behind the
  "Why this diagnosis" view (global GBM TreeSHAP importances, W=600 s).
- The page exposes the conformal / why containers and the script fetches
  the explain payload.
"""
import json

import pytest

from conftest import CLASSES, ENSEMBLE_W, N_STEPS, load_run

N_CLASSES = len(CLASSES)


def check_set(s, cls, field):
    assert isinstance(s, list) and len(s) >= 1, f"{cls}/{field}: empty set"
    assert all(isinstance(i, int) and 0 <= i < N_CLASSES for i in s), \
        f"{cls}/{field}: class index out of range"
    assert len(set(s)) == len(s), f"{cls}/{field}: duplicate class index"


@pytest.mark.parametrize("cls", CLASSES)
@pytest.mark.parametrize("model", ["rf", "gbm"])
def test_conf_per_step_sets(repo_root, cls, model):
    run = load_run(repo_root, cls)
    conf = run["conf"]
    sets = conf[model]
    assert len(sets) == N_STEPS, f"{cls}/{model}: {len(sets)} steps"
    proba = run["proba"] if model == "rf" else run["proba_gbm"]
    for k, s in enumerate(sets):
        check_set(s, cls, f"conf.{model}[{k}]")
        top1 = max(range(N_CLASSES), key=lambda i: proba[k][i])
        assert top1 in s, f"{cls}/{model}[{k}]: argmax class not in LAC set"


@pytest.mark.parametrize("cls", CLASSES)
def test_conf_ensemble_sets(repo_root, cls):
    run = load_run(repo_root, cls)
    ens = run["conf"]["ens"]
    assert sorted(ens.keys()) == sorted(ENSEMBLE_W)
    for w, s in ens.items():
        check_set(s, cls, f"conf.ens[{w}]")
        row = run["proba_ens"][w]
        top1 = max(range(N_CLASSES), key=lambda i: row[i])
        assert top1 in s, f"{cls}/conf.ens[{w}]: argmax class not in LAC set"


def test_explain_json_contract(repo_root):
    with open(repo_root / "data" / "explain.json", encoding="utf-8") as f:
        ex = json.load(f)
    assert ex["classes"] == CLASSES
    per_class = ex["per_class_top_sensors"]
    assert sorted(per_class.keys()) == sorted(CLASSES)
    for cls, entries in per_class.items():
        assert len(entries) == 8, f"{cls}: {len(entries)} sensors, want 8"
        for e in entries:
            assert set(e) >= {"code", "name", "importance"}, (cls, e)
            assert isinstance(e["importance"], (int, float))
            assert e["importance"] > 0, (cls, e)
    assert len(ex["global_top_sensors"]) >= 1


def test_page_exposes_conformal_and_why_views(repo_root):
    index = (repo_root / "index.html").read_text(encoding="utf-8")
    app = (repo_root / "app.js").read_text(encoding="utf-8")
    assert 'id="confBox"' in index
    assert 'id="whyBox"' in index
    assert "fetch('data/explain.json')" in app
