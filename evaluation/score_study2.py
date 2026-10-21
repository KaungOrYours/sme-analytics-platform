"""
Study 2 scoring (docs/study2_protocol.md Section 7, PRE-REGISTERED 2026-10-21).

Scores all six diagnostics against all three failure labels, for one dataset
group, reusing Study 1's scoring primitives unchanged (`score_rq2.py`'s
confusion matrix, MCC-with-degenerate-rule, precision/recall/false-alarm, and
run-level aggregate bootstrap) so that Study 2's numbers are computed by exactly
the same machinery that produced Study 1's and are directly comparable.

Scope, carried forward from Study 1's 2026-10-20 addendum: **automated-pipeline
runs only.** The manual baseline's diagnostics are recorded on every run but are
not scored -- RQ2/RQ4-RQ7 are about whether the automated pipeline's own signals
predict its own failures, not about a pooled sample across two pipelines.

Breakdowns produced, all pre-registered:
  - overall (all conditions pooled)
  - per corruption family (clean / missing_values / duplicates / outliers)
  - D2 only: stratified by `forces_duplication`, per Section 5's declared
    requirement that fold contamination be reported separately for datasets
    whose feature space is too small to hold n distinct rows (where duplicate
    rows are arithmetically unavoidable rather than a data defect)

Usage:
    python -m evaluation.score_study2 A
    python -m evaluation.score_study2 B
    python -m evaluation.score_study2 C
"""
import argparse
import json
from pathlib import Path

from evaluation.diagnostics2 import DIAGNOSTIC_NAMES, LABEL_NAMES
from evaluation.score_rq2 import (
    bootstrap_aggregate_metrics,
    confusion,
    mcc,
    precision_recall_far,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_runs(group):
    path = RESULTS_DIR / f"study2_group_{group}_results.json"
    if not path.exists():
        raise SystemExit(
            f"{path} not found. Run `python -m evaluation.full_run_study2 {group}` first."
        )
    with open(path) as f:
        return json.load(f)["runs"]


def score_one(diagnostic, label, runs, seed=0):
    """Confusion matrix + metrics + bootstrap CI for one (diagnostic, label)
    pair. Runs where the diagnostic is undefined (None) are excluded and
    counted, never silently coerced to False."""
    trig, poor, undefined = [], [], 0
    for r in runs:
        a = r["automated"]
        t = a["triggered"][diagnostic]
        if t is None:
            undefined += 1
            continue
        trig.append(bool(t))
        poor.append(bool(a["labels"][label]))

    if not trig:
        return {
            "diagnostic": diagnostic,
            "label": label,
            "n_runs": 0,
            "n_undefined": undefined,
            "note": "no runs with a defined diagnostic value",
        }

    tp, fp, fn, tn = confusion(trig, poor)
    precision, recall, far = precision_recall_far(tp, fp, fn, tn)
    degenerate = (tp + fp) == 0 or (tp + fn) == 0 or (tn + fp) == 0 or (tn + fn) == 0
    return {
        "diagnostic": diagnostic,
        "label": label,
        "n_runs": len(trig),
        "n_undefined": undefined,
        "n_poor": sum(poor),
        "n_triggered": sum(trig),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "false_alarm_rate": far,
        "mcc": mcc(tp, fp, fn, tn),
        # Frozen Study 1 Section 6 rule: MCC = 0 for a degenerate matrix. Flagged
        # per the protocol's requirement that every firing of the rule is stated.
        "degenerate": degenerate,
        "aggregate_bootstrap_ci": bootstrap_aggregate_metrics(trig, poor, seed=seed),
    }


def families(runs):
    seen = []
    for r in runs:
        if r["corruption_type"] not in seen:
            seen.append(r["corruption_type"])
    return seen


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("group", choices=["A", "B", "C"])
    args = ap.parse_args()
    runs = load_runs(args.group)

    out = {
        "group": args.group,
        "protocol": "docs/study2_protocol.md (pre-registered 2026-10-21)",
        "scope": "automated-pipeline runs only (Study 1 addendum, carried forward)",
        "n_runs_total": len(runs),
        "overall": {},
        "by_corruption_family": {},
        "fold_contamination_by_forced_duplication": {},
    }

    for label in LABEL_NAMES:
        out["overall"][label] = {
            d: score_one(d, label, runs) for d in DIAGNOSTIC_NAMES
        }

    for fam in families(runs):
        subset = [r for r in runs if r["corruption_type"] == fam]
        out["by_corruption_family"][fam] = {
            label: {d: score_one(d, label, subset) for d in DIAGNOSTIC_NAMES}
            for label in LABEL_NAMES
        }

    # Section 5's declared stratification for D2.
    for forced in (True, False):
        subset = [r for r in runs if r["forces_duplication"] is forced]
        key = "forced_duplication" if forced else "not_forced"
        out["fold_contamination_by_forced_duplication"][key] = {
            "n_runs": len(subset),
            "datasets": sorted({r["dataset"] for r in subset}),
            "scores": (
                {
                    label: score_one("fold_contamination_gt_0.10", label, subset)
                    for label in LABEL_NAMES
                }
                if subset
                else None
            ),
        }

    path = RESULTS_DIR / f"study2_group_{args.group}_scores.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2)

    # Console summary: primary label first, since it is Study 1's label verbatim.
    print(f"\n=== Study 2, group {args.group} ({len(runs)} runs, automated only) ===")
    for label in LABEL_NAMES:
        base = out["overall"][label][DIAGNOSTIC_NAMES[0]]
        print(f"\n--- label: {label}  (poor = {base.get('n_poor')}/{base.get('n_runs')}) ---")
        print(f"{'diagnostic':30s} {'TP':>3s} {'FP':>3s} {'FN':>3s} {'TN':>3s} "
              f"{'prec':>6s} {'rec':>6s} {'FAR':>6s} {'MCC':>7s}  CI(MCC)")
        for d in DIAGNOSTIC_NAMES:
            s = out["overall"][label][d]
            if "tp" not in s:
                print(f"{d:30s}  (undefined on all runs)")
                continue
            ci = s["aggregate_bootstrap_ci"]["mcc"]
            fmt = lambda v: f"{v:6.3f}" if v is not None else "     -"
            flag = " DEGEN" if s["degenerate"] else ""
            print(f"{d:30s} {s['tp']:3d} {s['fp']:3d} {s['fn']:3d} {s['tn']:3d} "
                  f"{fmt(s['precision'])} {fmt(s['recall'])} {fmt(s['false_alarm_rate'])} "
                  f"{s['mcc']:7.3f}  [{ci['ci_lower']:.2f}, {ci['ci_upper']:.2f}]{flag}")
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
