"""
RQ2 scoring (docs/evaluation_protocol.md Sections 4-6, 9): scores the two
diagnostics (n/p, sigma_CV) as binary predictors of "poor" (G > delta_G),
plus the bootstrap CI on each run's S_test.

Scope (decided 2026-10-20, recorded in docs/evaluation_protocol.md's
addendum): diagnostics are scored on AUTOMATED-pipeline runs only. RQ2 and
the dissertation's novelty claim concern whether the automated pipeline's
own signals predict its own failures -- not a pooled automated+manual
sample. The manual baseline's G is used only for the RQ1 comparison
(elsewhere), not fed into this diagnostic scoring.

Usage: python -m evaluation.score_rq2 development
       python -m evaluation.score_rq2 final-evaluation
"""
import json
import sys
from pathlib import Path

import numpy as np

RESULTS_DIR = Path(__file__).resolve().parent / "results"

DELTA_G = 0.05
NP_THRESHOLD = 10       # n/p < 10 triggers
SIGMA_CV_THRESHOLD = 0.10  # sigma_cv > 0.10 triggers
N_BOOTSTRAP = 1000


def poor_label(run):
    return 1 if run["automated"]["G"] > DELTA_G else 0


def np_triggered(run):
    a = run["automated"]
    return 1 if (a["n"] / a["p"]) < NP_THRESHOLD else 0


def sigma_cv_triggered(run):
    sigma = run["automated"]["sigma_cv"]
    return 1 if (sigma is not None and sigma > SIGMA_CV_THRESHOLD) else 0


def confusion(triggered, poor):
    tp = sum(1 for t, p in zip(triggered, poor) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(triggered, poor) if t == 1 and p == 0)
    fn = sum(1 for t, p in zip(triggered, poor) if t == 0 and p == 1)
    tn = sum(1 for t, p in zip(triggered, poor) if t == 0 and p == 0)
    return tp, fp, fn, tn


def mcc(tp, fp, fn, tn):
    """MCC = 0 if any marginal sum is zero (degenerate confusion matrix),
    matching sklearn's matthews_corrcoef convention -- frozen rule, Section 6."""
    numerator = tp * tn - fp * fn
    denom_sq = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    if denom_sq == 0:
        return 0.0
    return numerator / np.sqrt(denom_sq)


def precision_recall_far(tp, fp, fn, tn):
    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None
    far = fp / (fp + tn) if (fp + tn) > 0 else None  # false-alarm rate
    return precision, recall, far


def bootstrap_aggregate_metrics(triggered, poor, seed=0, n_resamples=N_BOOTSTRAP):
    """Group-level uncertainty on precision/recall/false-alarm-rate/MCC
    (docs/evaluation_protocol.md Section 9: 'a separate quantity from the
    per-run S_test interval ... not yet specified; decide before the
    RQ2/RQ3 analysis step' -- decided here, 2026-10-20).

    Method: non-parametric bootstrap over the RUN as the resampling unit
    (resample n runs with replacement from the n runs in the group, n =
    group size, recompute the confusion matrix and all 4 metrics each
    time). Explicit limitation, stated wherever this is reported: runs
    within a group are not fully independent (4 development datasets each
    contribute 9 runs via 3 rates x 3 seeds, so resampling at the run level
    treats correlated runs as exchangeable -- a cluster bootstrap over
    datasets would respect that structure better, but with only 3-4
    clusters per group it would be far noisier, not more rigorous.
    Flagged as a limitation, not hidden."""
    triggered = np.array(triggered)
    poor = np.array(poor)
    n = len(triggered)
    rng = np.random.default_rng(seed)
    precisions, recalls, fars, mccs = [], [], [], []
    for _ in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        tp, fp, fn, tn = confusion(triggered[idx], poor[idx])
        precision, recall, far = precision_recall_far(tp, fp, fn, tn)
        if precision is not None:
            precisions.append(precision)
        if recall is not None:
            recalls.append(recall)
        if far is not None:
            fars.append(far)
        mccs.append(mcc(tp, fp, fn, tn))

    def summarise(vals):
        if not vals:
            return None
        arr = np.array(vals)
        return {
            "bootstrap_mean": float(arr.mean()),
            "ci_lower": float(np.percentile(arr, 2.5)),
            "ci_upper": float(np.percentile(arr, 97.5)),
            "n_valid_resamples": len(arr),
        }

    return {
        "precision": summarise(precisions), "recall": summarise(recalls),
        "false_alarm_rate": summarise(fars), "mcc": summarise(mccs),
    }


def score_diagnostic(name, triggered, poor):
    tp, fp, fn, tn = confusion(triggered, poor)
    precision, recall, far = precision_recall_far(tp, fp, fn, tn)
    m = mcc(tp, fp, fn, tn)
    degenerate = any(s == 0 for s in [(tp + fp), (tp + fn), (tn + fp), (tn + fn)])
    agg_ci = bootstrap_aggregate_metrics(triggered, poor)
    print(f"\n{name}:")
    print(f"  confusion (triggered x poor): TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"  precision={precision if precision is None else round(precision,3)} "
          f"recall={recall if recall is None else round(recall,3)} "
          f"false_alarm_rate={far if far is None else round(far,3)} "
          f"MCC={round(m,3)}{'  (degenerate confusion matrix -> MCC forced 0)' if degenerate else ''}")
    for metric_name, ci in agg_ci.items():
        if ci:
            print(f"  {metric_name} 95% bootstrap CI: [{ci['ci_lower']:.3f}, {ci['ci_upper']:.3f}] "
                  f"(bootstrap mean {ci['bootstrap_mean']:.3f}, n_resamples={ci['n_valid_resamples']})")
        else:
            print(f"  {metric_name} 95% bootstrap CI: undefined (no resample had a valid denominator)")
    return {
        "name": name, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "false_alarm_rate": far,
        "mcc": m, "degenerate": degenerate, "aggregate_bootstrap_ci": agg_ci,
    }


def bootstrap_ci_s_test(y_test, test_proba, seed, n_resamples=N_BOOTSTRAP):
    """Paired, class-stratified bootstrap CI on S_test (AUROC). Resamples
    (label, prediction) pairs together, within each class separately, then
    recombines -- per Section 9. Uncertainty on test-set sampling only."""
    from sklearn.metrics import roc_auc_score

    y = np.array(y_test)
    p = np.array(test_proba)
    rng = np.random.default_rng(seed)
    pos_idx = np.where(y == 1)[0]
    neg_idx = np.where(y == 0)[0]

    if len(pos_idx) == 0 or len(neg_idx) == 0:
        return None  # AUROC undefined without both classes present

    scores = []
    for _ in range(n_resamples):
        resampled_pos = rng.choice(pos_idx, size=len(pos_idx), replace=True)
        resampled_neg = rng.choice(neg_idx, size=len(neg_idx), replace=True)
        idx = np.concatenate([resampled_pos, resampled_neg])
        y_r, p_r = y[idx], p[idx]
        if len(set(y_r)) < 2:
            continue
        scores.append(roc_auc_score(y_r, p_r))

    if not scores:
        return None
    scores = np.array(scores)
    return {
        "ci_lower": float(np.percentile(scores, 2.5)),
        "ci_upper": float(np.percentile(scores, 97.5)),
        "n_valid_resamples": len(scores),
    }


KNOWN_GROUPS = {"development": "development_results.json", "final-evaluation": "final_evaluation_results.json"}


def resolve_results_path(arg):
    """Accepts either a known Experiment-1 group name (backward compatible
    with the original development/final-evaluation invocation) or any
    literal results-file stem for an extended experiment, e.g.
    'development_duplicates' -> development_duplicates_results.json."""
    if arg in KNOWN_GROUPS:
        return RESULTS_DIR / KNOWN_GROUPS[arg]
    return RESULTS_DIR / f"{arg}_results.json"


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m evaluation.score_rq2 {development|final-evaluation|<results-file-stem>}")
        print("  e.g. python -m evaluation.score_rq2 development_duplicates")
        sys.exit(1)
    group = sys.argv[1]
    results_path = resolve_results_path(group)
    if not results_path.exists():
        print(f"No results file at {results_path}")
        sys.exit(1)
    results = json.loads(results_path.read_text())

    poor = [poor_label(r) for r in results]
    print(f"Group: {group} ({len(results)} automated-pipeline runs)")
    print(f"Poor runs (G > {DELTA_G}): {sum(poor)}/{len(poor)} ({100*sum(poor)/len(poor):.1f}%)")

    np_scored = score_diagnostic(f"n/p < {NP_THRESHOLD}", [np_triggered(r) for r in results], poor)
    sigma_scored = score_diagnostic(f"sigma_cv > {SIGMA_CV_THRESHOLD}", [sigma_cv_triggered(r) for r in results], poor)

    print("\nPer-run bootstrap CI on S_test (automated pipeline, 95%, paired+stratified, 1000 resamples):")
    ci_rows = []
    for r in results:
        a = r["automated"]
        # Experiment 1 results use "missing_rate" (always the missing-values
        # family); extended-experiment results (full_run_extended.py) use
        # "corruption_type" + "rate" to cover duplicates/outliers too.
        if "missing_rate" in r:
            corruption_label = f"missing_values rate={r['missing_rate']:.2f}"
            rate_value = r["missing_rate"]
            corruption_type = "missing_values"
        else:
            corruption_label = f"{r['corruption_type']} rate={r['rate']:.2f}"
            rate_value = r["rate"]
            corruption_type = r["corruption_type"]
        ci = bootstrap_ci_s_test(a["y_test"], a["test_proba"], seed=r["seed"])
        ci_rows.append({
            "dataset": r["dataset"], "seed": r["seed"], "corruption_type": corruption_type,
            "rate": rate_value, "s_test": a["s_test"], "G": a["G"], "poor": poor_label(r),
            "n": a["n"], "p": a["p"], "sigma_cv": a["sigma_cv"],
            "ci": ci,
        })
        ci_str = f"[{ci['ci_lower']:.3f}, {ci['ci_upper']:.3f}]" if ci else "undefined (single class)"
        print(f"  {r['dataset']:30s} {corruption_label} seed={r['seed']} "
              f"S_test={a['s_test']:.4f} CI={ci_str}")

    out = {
        "group": group, "delta_g": DELTA_G, "np_threshold": NP_THRESHOLD,
        "sigma_cv_threshold": SIGMA_CV_THRESHOLD, "n_runs": len(results),
        "n_poor": sum(poor), "np_diagnostic": np_scored, "sigma_cv_diagnostic": sigma_scored,
        "per_run": ci_rows,
    }
    out_path = RESULTS_DIR / f"{group.replace('-', '_')}_rq2_scores.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote RQ2 scoring to {out_path}")


if __name__ == "__main__":
    main()
