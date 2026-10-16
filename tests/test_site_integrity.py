"""Site integrity: the served page and script must be structurally sane.

- index.html carries the diagnosis-model toggle (select#modelSel) with
  exactly the three served models, plus the importmap that wires the
  vendored Three.js modules.
- app.js parses as an ES module (node --check on a .mjs copy) and
  defines the same three models with the same display labels the
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
    "gbm": "Gradient Boosting (LightGBM)",
    "ens": "Ensemble (RF + GBM + TCN)",
}


def test_index_has_model_toggle_with_three_options():
    m = re.search(r'<select id="modelSel">(.*?)</select>', INDEX, re.S)
    assert m, "index.html is missing <select id=\"modelSel\">"
    options = re.findall(r'value="([^"]+)"[^>]*>([^<]+)</option>', m.group(1))
    assert dict(options) == EXPECTED_MODELS


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


def test_appjs_models_match_toggle():
    for key, label in EXPECTED_MODELS.items():
        pat = rf"{key}:\s*\{{[^}}]*label:\s*'{re.escape(label)}'"
        assert re.search(pat, APP), f"app.js MODELS missing {key} ({label})"


def test_appjs_fetches_baked_data():
    assert "fetch('data/manifest.json')" in APP
    assert "fetch('data/' + meta.data)" in APP


def test_appjs_ensemble_steps_are_the_gated_windows():
    # ENS_STEP_W maps step k -> W key; k=6/12/30/60 <-> W=60/120/300/600.
    m = re.search(r"ENS_STEP_W\s*=\s*\{([^}]*)\}", APP)
    assert m
    pairs = dict(re.findall(r"(\d+):\s*'(\d+)'", m.group(1)))
    assert pairs == {"6": "60", "12": "120", "30": "300", "60": "600"}


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
