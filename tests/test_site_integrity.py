"""Site integrity: the served page and script must be structurally sane.

- index.html presents the twin's single diagnosis model — the Random
  Forest of Task E item E2 — plus the importmap that wires the
  vendored Three.js modules. There is NO model toggle: the Gradient
  Boosting / Ensemble entries the twin briefly served were removed in
  the Homework 2 alignment (the assignment's Task E model list is
  logistic regression / random forest and the CNN / LSTM / GRU family).
- app.js parses as an ES module (node --check on a .mjs copy) and
  defines the same single model with the same display label the
  registry uses.
"""
import json
import pathlib
import re
import shutil
import subprocess

import pytest

from conftest import REPO_ROOT

APP = (REPO_ROOT / "app.js").read_text(encoding="utf-8")
INDEX = (REPO_ROOT / "index.html").read_text(encoding="utf-8")

EXPECTED_MODELS = {
    "rf": "Random Forest",
}

REMOVED_MODELS = {
    "gbm": "Gradient Boosting (LightGBM)",
    "ens": "Ensemble (RF + GBM + TCN)",
}


def test_index_presents_only_the_random_forest():
    assert 'id="modelSel"' not in INDEX, "the model toggle should be gone"
    assert 'id="modelTag"' in INDEX
    for label in REMOVED_MODELS.values():
        assert label not in INDEX, f"removed model still in index.html: {label}"


def test_index_loads_app_and_styles():
    assert 'src="app.js"' in INDEX
    assert 'href="styles.css"' in INDEX
    assert 'id="modelTag"' in INDEX


def test_index_importmap_points_at_vendor():
    m = re.search(r'<script type="importmap">(.*?)</script>', INDEX, re.S)
    assert m, "index.html is missing the importmap"
    im = json.loads(m.group(1))
    assert im["imports"]["three"] == "./vendor/three.module.js"
    assert im["imports"]["three/addons/"] == "./vendor/"


def test_appjs_models_match_page():
    for key, label in EXPECTED_MODELS.items():
        pat = rf"{key}:\s*\{{[^}}]*label:\s*'{re.escape(label)}'"
        assert re.search(pat, APP), f"app.js MODELS missing {key} ({label})"
    for label in REMOVED_MODELS.values():
        assert label not in APP, f"removed model still in app.js: {label}"
    assert "proba_gbm" not in APP
    assert "proba_ens" not in APP


def test_appjs_fetches_baked_data():
    assert "fetch('data/manifest.json')" in APP
    assert "fetch('data/' + meta.data)" in APP


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_appjs_parses_as_es_module(tmp_path):
    probe = tmp_path / "app_check.mjs"
    probe.write_text(APP, encoding="utf-8")
    r = subprocess.run(["node", "--check", str(probe)],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"node --check failed:\n{r.stderr}"


def test_vendor_files_present():
    for rel in ("vendor/three.module.js", "vendor/OrbitControls.js",
                "vendor/LICENSE.txt", "styles.css", "app.js", "index.html"):
        p = REPO_ROOT / rel
        assert p.is_file() and p.stat().st_size > 0, f"missing {rel}"
