"""Advanced-model probability blocks vs the addendum reference snapshot.

The twin serves two advanced models baked from the Task E
advanced-modeling addendum's export (twin_advanced_probs.json):

- Gradient Boosting (LightGBM): `proba_gbm`, present at ALL 60 steps.
- Ensemble (RF + GBM + TCN): `proba_ens`, present ONLY at the windows
  its members were evaluated at — W = 60/120/300/600 s (steps
  k = 6/12/30/60). Any other key would mean fabricated interpolation.

tests/reference_advanced_probs.json snapshots the export; the baked
blocks must equal it exactly. A deliberate re-bake updates both.
"""
import json
import pathlib

import pytest

from conftest import CLASSES, ENSEMBLE_W, REPO_ROOT, SUM_TOL, load_run
from test_data_contracts import check_block

REF = json.loads((pathlib.Path(__file__).parent
                  / "reference_advanced_probs.json").read_text(encoding="utf-8"))


def test_reference_classes_match_manifest_order():
    assert REF["classes"] == CLASSES
    assert sorted(REF["runs"]) == sorted(CLASSES)


@pytest.mark.parametrize("cls", CLASSES)
def test_gbm_present_at_all_steps_and_valid(repo_root, cls):
    run = load_run(repo_root, cls)
    assert "proba_gbm" in run, f"{cls}: proba_gbm missing"
    check_block(run["proba_gbm"], cls, "proba_gbm")


@pytest.mark.parametrize("cls", CLASSES)
def test_ensemble_only_at_evaluated_windows(repo_root, cls):
    run = load_run(repo_root, cls)
    assert "proba_ens" in run, f"{cls}: proba_ens missing"
    assert sorted(run["proba_ens"], key=int) == ENSEMBLE_W, \
        f"{cls}: ensemble windows {sorted(run['proba_ens'])} != {ENSEMBLE_W}"
    for w, row in run["proba_ens"].items():
        assert len(row) == len(CLASSES)
        assert all(0.0 <= v <= 1.0 for v in row)
        assert abs(sum(row) - 1.0) <= SUM_TOL, f"{cls}/ens W={w} sum {sum(row)}"


@pytest.mark.parametrize("cls", CLASSES)
def test_baked_blocks_equal_addendum_export(repo_root, cls):
    run = load_run(repo_root, cls)
    ref = REF["runs"][cls]
    assert run["severity"] == ref["severity"]
    assert run["file"] == ref["file"]
    assert run["proba_gbm"] == ref["gbm_proba"], \
        f"{cls}: proba_gbm differs from the addendum export"
    assert run["proba_ens"] == ref["ensemble_proba_by_W"], \
        f"{cls}: proba_ens differs from the addendum export"
