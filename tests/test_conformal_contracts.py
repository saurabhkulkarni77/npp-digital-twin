"""Contracts for the round-2 twin additions (Task E advanced round 2),
as aligned to the homework model list on 2026-10-19.

- Every baked run carries a `conf` block of 90% LAC split-conformal
  prediction sets for the Random Forest — one set per diagnosis step
  k = 1..60. A LAC set built from a probability row always contains
  that row's argmax class. (The block briefly also carried GBM and
  ensemble sets; those models are not in the assignment's Task E model
  list and were removed with their probability blocks.)
- The page exposes the conformal container.
"""
import pytest

from conftest import CLASSES, N_STEPS, load_run

N_CLASSES = len(CLASSES)


def check_set(s, cls, field):
    assert isinstance(s, list) and len(s) >= 1, f"{cls}/{field}: empty set"
    assert all(isinstance(i, int) and 0 <= i < N_CLASSES for i in s), \
        f"{cls}/{field}: class index out of range"
    assert len(set(s)) == len(s), f"{cls}/{field}: duplicate class index"


@pytest.mark.parametrize("cls", CLASSES)
def test_conf_per_step_sets(repo_root, cls):
    run = load_run(repo_root, cls)
    conf = run["conf"]
    assert set(conf) - {"_about"} == {"rf"}, \
        f"{cls}: conf models {sorted(conf)}"
    sets = conf["rf"]
    assert len(sets) == N_STEPS, f"{cls}/rf: {len(sets)} steps"
    proba = run["proba"]
    for k, s in enumerate(sets):
        check_set(s, cls, f"conf.rf[{k}]")
        top1 = max(range(N_CLASSES), key=lambda i: proba[k][i])
        assert top1 in s, f"{cls}/rf[{k}]: argmax class not in LAC set"


@pytest.mark.parametrize("cls", CLASSES)
def test_removed_model_blocks_absent(repo_root, cls):
    run = load_run(repo_root, cls)
    assert "proba_gbm" not in run, f"{cls}: proba_gbm still baked"
    assert "proba_ens" not in run, f"{cls}: proba_ens still baked"
    assert "gbm" not in run["conf"], f"{cls}: conf.gbm still baked"
    assert "ens" not in run["conf"], f"{cls}: conf.ens still baked"


def test_page_exposes_conformal_view(repo_root):
    index = (repo_root / "index.html").read_text(encoding="utf-8")
    assert 'id="confBox"' in index
