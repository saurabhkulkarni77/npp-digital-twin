"""Data contracts for the baked runs (data/manifest.json + run_*.json).

Every run file must describe the same plant response the page renders:
63 frames on the t = 0..620 s axis, the manifest's 17 channels with one
series per frame, and a 60-step Random Forest probability block whose
rows are valid 12-class distributions in the canonical class order.
"""
import pytest

from conftest import (CLASSES, N_CHANNELS, N_FRAMES, N_STEPS, SUM_TOL,
                      T_ONSET, load_run)


def test_manifest_classes_and_channels(manifest):
    assert manifest["classes"] == CLASSES
    assert len(manifest["channels"]) == N_CHANNELS
    assert manifest["t0_onset_s"] == T_ONSET
    for code, meta in manifest["channels"].items():
        assert set(meta) >= {"name", "unit"}, code
    for ch in manifest["default_chart_channels"]:
        assert ch in manifest["channels"]


def test_manifest_runs_cover_all_classes(manifest):
    runs = manifest["runs"]
    assert [r["id"] for r in runs] == CLASSES
    for r in runs:
        assert r["class"] == r["id"]
        assert r["data"] == f"run_{r['id']}.json"
        assert r["file"] == f"{r['id']}/{r['severity']:g}.csv"
        assert set(r["break"]) >= {"kind", "loop"}


@pytest.mark.parametrize("cls", CLASSES)
def test_run_time_axis(repo_root, cls):
    run = load_run(repo_root, cls)
    assert run["class"] == cls
    assert run["split"] == "test"
    assert run["times"] == [10.0 * i for i in range(N_FRAMES)]


@pytest.mark.parametrize("cls", CLASSES)
def test_run_channels(repo_root, manifest, cls):
    run = load_run(repo_root, cls)
    assert set(run["channels"]) == set(manifest["channels"])
    for code, series in run["channels"].items():
        assert len(series) == N_FRAMES, f"{cls}/{code}: {len(series)} frames"
        assert all(isinstance(v, (int, float)) for v in series)


@pytest.mark.parametrize("cls", CLASSES)
def test_run_matches_manifest(repo_root, manifest, cls):
    run = load_run(repo_root, cls)
    meta = next(r for r in manifest["runs"] if r["id"] == cls)
    assert run["severity"] == meta["severity"]
    assert run["file"] == meta["file"]
    assert run["break"] == meta["break"]


def check_block(rows, cls, field):
    assert len(rows) == N_STEPS, f"{cls}/{field}: {len(rows)} steps"
    for i, row in enumerate(rows):
        assert len(row) == len(CLASSES), f"{cls}/{field}[{i}]: {len(row)}"
        assert all(0.0 <= v <= 1.0 for v in row), f"{cls}/{field}[{i}] range"
        assert abs(sum(row) - 1.0) <= SUM_TOL, \
            f"{cls}/{field}[{i}] sums to {sum(row)}"


@pytest.mark.parametrize("cls", CLASSES)
def test_run_rf_proba_contract(repo_root, cls):
    run = load_run(repo_root, cls)
    check_block(run["proba"], cls, "proba")
