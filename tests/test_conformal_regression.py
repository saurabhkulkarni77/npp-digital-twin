"""Regression guard: the conformal feature stays REMOVED.

The 90% LAC split-conformal prediction sets (Task E advanced round 2)
were baked into the twin on 2026-10-19 — a `conf` block in every run
file, read by a `currentConfSet` helper in app.js and shown as chips
in a `confBox` panel. They were removed later the same day, when all
advanced modeling was dropped from Homework 2: the twin serves the
core homework diagnosis only (the Random Forest's per-step
probabilities). These tests fail if the feature ever comes back.
"""
import pytest

from conftest import CLASSES, load_run

APP_TOKENS = ("conformal", "currentConfSet", "confBox", "confSet",
              "confNote", "conf-chip")


@pytest.mark.parametrize("cls", CLASSES)
def test_run_files_carry_no_conf_block(repo_root, cls):
    run = load_run(repo_root, cls)
    assert "conf" not in run, f"{cls}: conf block still baked"
    assert "proba_gbm" not in run, f"{cls}: proba_gbm still baked"
    assert "proba_ens" not in run, f"{cls}: proba_ens still baked"


def test_page_has_no_conformal_view(repo_root):
    index = (repo_root / "index.html").read_text(encoding="utf-8")
    assert 'id="confBox"' not in index
    assert "conformal" not in index.lower()


def test_script_has_no_conformal_logic(repo_root):
    app = (repo_root / "app.js").read_text(encoding="utf-8")
    assert "conformal" not in app.lower()
    for tok in APP_TOKENS[1:]:
        assert tok not in app, f"app.js still references {tok}"


def test_styles_have_no_conf_chip_rules(repo_root):
    css = (repo_root / "styles.css").read_text(encoding="utf-8")
    assert ".conf-" not in css
