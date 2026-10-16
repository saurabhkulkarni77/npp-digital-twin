"""Internal asset/link resolution for the served twin.

Every relative href/src in index.html, every importmap target, and
every module import / data fetch in app.js must resolve to a file in
this repo — the twin is served as a plain static tree on GitHub Pages
and on S3, so a missing target is a live 404.
"""
import json
import re

from conftest import REPO_ROOT

INDEX = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
APP = (REPO_ROOT / "app.js").read_text(encoding="utf-8")


def local_refs(html):
    refs = re.findall(r'(?:href|src)="([^"]+)"', html)
    return [r for r in refs
            if not r.startswith(("http://", "https://", "#", "data:"))]


def test_index_relative_refs_resolve():
    refs = local_refs(INDEX)
    assert refs, "no relative refs found in index.html"
    for r in refs:
        assert (REPO_ROOT / r).is_file(), f"index.html references missing {r}"


def test_appjs_imports_resolve_via_importmap():
    im = json.loads(re.search(r'<script type="importmap">(.*?)</script>',
                              INDEX, re.S).group(1))["imports"]
    for spec in re.findall(r"from\s+'([^']+)'", APP):
        if spec == "three":
            target = im["three"]
        elif spec.startswith("three/addons/"):
            target = im["three/addons/"] + spec[len("three/addons/"):]
        else:
            raise AssertionError(f"unmapped import {spec}")
        assert (REPO_ROOT / target).is_file(), \
            f"import {spec} -> missing {target}"


def test_appjs_data_targets_exist(manifest):
    assert (REPO_ROOT / "data" / "manifest.json").is_file()
    for r in manifest["runs"]:
        assert (REPO_ROOT / "data" / r["data"]).is_file(), r["data"]
