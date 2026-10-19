#!/usr/bin/env python3
"""NPP digital twin MLOps monitor — integrity & availability checks.

Recomputes, from this repo's own baked artifacts plus two read-only
HTTP probes:

  * Run-data integrity: for each of the 12 runs, the RF block holds
    60 steps of valid 12-class distributions (rows sum to 1), the
    time axis is 63 frames, and the channel set matches the manifest.
  * Registry consistency: models/registry.json metrics equal the
    frozen models/baselines.json values (a drift between the two means
    the gate inputs no longer describe the accepted evaluation), and
    the registry's model name matches the label the page serves
    from app.js.
  * Live availability: both hostings answer HTTP 200 and serve the
    twin — GitHub Pages (index carries the diagnosis-model tag;
    app.js names the registry model) and the AWS S3 website endpoint
    (index 200 with the tag; one run JSON downloads and its rows
    sum to 1).

Writes a Markdown report (default ./monitor_report.md) and, when
running in GitHub Actions, sets the step outputs `breach` and
`breach_count`. Exit code is 0 when the checks ran (findings are
reported, not failed); operational errors (missing/corrupt local
inputs) exit 1 so a broken monitor is visible instead of silently
green. Live-probe failures are findings, not operational errors: a
hosting being down is exactly what this monitor exists to report.

Usage: python monitor/monitor.py [--root PATH] [--report PATH]
              [--no-live]
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.request

CLASSES = [
    "LOCA", "LOCAC", "SLBIC", "SLBOC", "SGATR", "SGBTR",
    "RW", "RI", "FLB", "MD", "LR", "LLB",
]
N_FRAMES = 63
N_STEPS = 60
SUM_TOL = 0.01
PAGES_URL = "https://saurabhkulkarni77.github.io/npp-digital-twin/"
AWS_URL = "http://npp-digital-twin-2026.s3-website-us-east-1.amazonaws.com/"
HTTP_TIMEOUT = 30


def load(root, *parts):
    with open(root.joinpath(*parts), encoding="utf-8") as f:
        return json.load(f)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "NPP-Twin-Monitor/1.0"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        return r.status, r.read().decode("utf-8", errors="replace")


def check_block(findings, cls, field, rows):
    if len(rows) != N_STEPS:
        findings.append(f"**{cls}** — `{field}` has {len(rows)} steps, "
                        f"expected {N_STEPS}.")
        return
    for i, row in enumerate(rows):
        if len(row) != len(CLASSES) or abs(sum(row) - 1.0) > SUM_TOL:
            findings.append(f"**{cls}** — `{field}` step {i + 1} is not a "
                            f"valid 12-class distribution (sum "
                            f"{sum(row):.4f}).")
            return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None,
                    help="repo root (default: parent of this script's dir)")
    ap.add_argument("--report", default="monitor_report.md")
    ap.add_argument("--no-live", action="store_true",
                    help="skip the live-hosting probes")
    args = ap.parse_args()

    root = (pathlib.Path(args.root).resolve() if args.root
            else pathlib.Path(__file__).resolve().parent.parent)

    findings = []   # breaches / inconsistencies -> issue
    notes = []      # informational

    # --- run-data integrity ---------------------------------------------
    manifest = load(root, "data", "manifest.json")
    if manifest["classes"] != CLASSES:
        findings.append("**Manifest** — class order differs from the "
                        "canonical 12-class order.")
    n_channels = len(manifest["channels"])
    for cls in CLASSES:
        run = load(root, "data", f"run_{cls}.json")
        if len(run["times"]) != N_FRAMES:
            findings.append(f"**{cls}** — {len(run['times'])} frames, "
                            f"expected {N_FRAMES}.")
        if set(run["channels"]) != set(manifest["channels"]):
            findings.append(f"**{cls}** — channel set differs from the "
                            "manifest.")
        check_block(findings, cls, "proba", run["proba"])
    notes.append(f"Run data: 12 runs checked — 63 frames, {n_channels} "
                 "channels, RF block at 60 steps.")

    # --- registry consistency --------------------------------------------
    registry = load(root, "models", "registry.json")
    baselines = load(root, "models", "baselines.json")
    for model in registry["models"]:
        base = baselines["test_macro_f1"].get(model["name"])
        if base is None:
            findings.append(f"**Registry** — {model['name']} has no "
                            "baseline entry.")
            continue
        for w, v in base.items():
            cur = model["test_macro_f1"].get(w)
            if cur != v:
                findings.append(
                    f"**Registry** — {model['name']} W={w} macro-F1 is "
                    f"{cur} in the registry but {v} in the frozen "
                    "baselines; the gate inputs are inconsistent.")
    app_js = (root / "app.js").read_text(encoding="utf-8")
    for model in registry["models"]:
        if f"label: '{model['name']}'" not in app_js:
            findings.append(f"**Registry** — {model['name']} is not a "
                            "label served by app.js.")
    notes.append("Registry: "
                 + ", ".join(f"{m['name']} "
                             f"{m['test_macro_f1']['120']}/"
                             f"{m['test_macro_f1']['300']}/"
                             f"{m['test_macro_f1']['600']}"
                             for m in registry["models"])
                 + " (test macro-F1 at W = 120/300/600 s, no-oracle).")

    # --- live availability ------------------------------------------------
    live_rows = []
    if args.no_live:
        notes.append("Live probes skipped (--no-live).")
    else:
        for name, base in (("GitHub Pages", PAGES_URL), ("AWS S3", AWS_URL)):
            try:
                status, body = fetch(base)
                ok = status == 200 and 'id="modelTag"' in body
                live_rows.append((name, base, status,
                                  "model tag present" if ok else "model tag MISSING"))
                if not ok:
                    findings.append(f"**Live {name}** — {base} answered "
                                    f"{status} but the diagnosis-model "
                                    "tag was not found in the served page.")
            except Exception as e:  # hosting down = finding, not a crash
                live_rows.append((name, base, "ERR", str(e)[:80]))
                findings.append(f"**Live {name}** — {base} unreachable: "
                                f"{e}")
        try:
            status, body = fetch(PAGES_URL + "app.js")
            named = all(m["name"] in body for m in registry["models"])
            if status != 200 or not named:
                findings.append("**Live GitHub Pages** — served app.js "
                                "does not name every registry model.")
        except Exception as e:
            findings.append(f"**Live GitHub Pages** — app.js fetch "
                            f"failed: {e}")
        try:
            status, body = fetch(AWS_URL + "data/run_LOCA.json")
            rows = json.loads(body)["proba"]
            if status != 200 or abs(sum(rows[-1]) - 1.0) > SUM_TOL:
                findings.append("**Live AWS S3** — run_LOCA.json served "
                                "but its probability rows do not sum "
                                "to 1.")
        except Exception as e:
            findings.append(f"**Live AWS S3** — run_LOCA.json check "
                            f"failed: {e}")
        notes.append("Live probes: both hostings fetched over HTTP; "
                     "Pages app.js and AWS run data spot-checked.")

    # --- report -----------------------------------------------------------
    today = dt.datetime.now(dt.timezone.utc).date()
    lines = [
        "## NPP Digital Twin — MLOps monitor report",
        "",
        f"Run date (UTC): {today}. Sources: this repo's baked run data "
        "and registry, plus read-only probes of the two live hostings.",
        "",
        "### Findings" if findings else "### Findings: none",
        "",
    ]
    lines += [f"- {f}" for f in findings] or ["- No integrity or "
                                              "availability problems."]
    lines += ["", "### Notes", ""] + [f"- {n}" for n in notes]
    if live_rows:
        lines += ["", "### Live hostings", "",
                  "| Hosting | URL | HTTP | Check |", "|---|---|---|---|"]
        for name, url, status, check in live_rows:
            lines.append(f"| {name} | {url} | {status} | {check} |")
    lines += [
        "",
        "This issue is opened/updated by `.github/workflows/monitor.yml` "
        "when findings exist; see `MLOPS.md`.",
        "",
    ]
    text = "\n".join(lines)
    pathlib.Path(args.report).write_text(text, encoding="utf-8")
    print(text)
    print(f"monitor: {len(findings)} finding(s)")

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"breach={'true' if findings else 'false'}\n")
            f.write(f"breach_count={len(findings)}\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, KeyError, ValueError) as e:
        print(f"::error::monitor operational failure: {e}")
        sys.exit(1)
