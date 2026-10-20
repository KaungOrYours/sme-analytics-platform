"""
SUPERSEDED (2026-10-19): built for the pre-approval research design, which
scored all 3 of automl.py's live reliability warnings (including
suspected_leakage). The approved PDM plan's RQ2 excludes any leakage-flag
diagnostic (docs/literature_matrix.md: no valid, deployable detector found
in the literature) and scores only n/p and sigma_cv, via
evaluation/score_rq2.py against evaluation/diagnostics.py's output -- see
docs/results_summary.md for the current results. This file's scoring logic
for n/p and sigma_cv was superseded by score_rq2.py's bootstrap-CI version;
its suspected_leakage scoring has no equivalent in the approved design at
all. Kept as a working reference, not a source of current results.

RQ2 (the primary novelty claim): scores each reliability warning from
backend/services/automl.py's build_reliability_warnings() as a binary
predictor of poor held-out performance.

Implements the locked "poor performance" definition from
docs/evaluation_protocol.md Section 4 exactly as written there — do not
loosen these thresholds after seeing results; if the definition turns out to
mislabel everything (or nothing) as poor, that is itself a finding to report,
per the protocol doc.
"""
import pandas as pd

try:
    from sklearn.metrics import roc_auc_score
except ImportError:  # pragma: no cover
    roc_auc_score = None

# Gap thresholds for the "unstable" half of the poor-performance definition.
# Stated design choices (evaluation_protocol.md Section 4), not validated
# standards.
GAP_THRESHOLDS = {"classification": 0.10, "regression": 0.15}


def majority_class_baseline(y):
    """Trivial-baseline accuracy: always predict the most frequent class."""
    counts = pd.Series(y).value_counts(normalize=True)
    return float(counts.max()) if len(counts) else None


def is_poor_performance(problem_type, cv_score, test_score, y_test=None, majority_baseline=None):
    """
    Locked definition, checked on the held-out test fold only:
    - weak: test score <= majority-class baseline (classification, pass
      y_test or a precomputed majority_baseline) or test R2 <= 0 (regression)
    - unstable: |cv_score - test_score| > 0.10 (classification) or > 0.15 (R2)
    Either condition alone is sufficient. Returns (is_poor: bool, detail dict
    distinguishing which condition fired, since a run can be weak without
    being unstable and vice versa).
    """
    if problem_type == "classification":
        if majority_baseline is None:
            if y_test is None:
                raise ValueError("classification needs y_test or majority_baseline")
            majority_baseline = majority_class_baseline(y_test)
        weak = test_score <= majority_baseline if majority_baseline is not None else False
        gap_threshold = GAP_THRESHOLDS["classification"]
    elif problem_type == "regression":
        weak = test_score <= 0
        gap_threshold = GAP_THRESHOLDS["regression"]
    else:
        raise ValueError(f"Unsupported problem_type: {problem_type}")

    unstable = abs(cv_score - test_score) > gap_threshold
    return bool(weak or unstable), {"weak": bool(weak), "unstable": bool(unstable)}


# Orientation of each warning's raw "value" relative to "more likely poor",
# used only for the AUROC discrimination score below. low_rows_to_features
# and unstable_cv have a clear, argued direction. suspected_leakage's
# direction is NOT assumed to be clean: a high CV score coincides with poor
# test performance only when the high score was inflated by leakage, not
# when the model is genuinely good — so weak/no discrimination for this one
# would itself be a reportable result, not a bug in this scoring code.
WARNING_DIRECTIONS = {
    "low_rows_to_features_ratio": -1,
    "unstable_cross_validation": 1,
    "suspected_leakage": 1,
}


def score_warning(warning_name, records):
    """
    records: list of {"triggered": bool, "value": float|None, "poor": bool},
    one entry per evaluation run, for a single warning.
    Returns precision, recall, false-alarm rate, and AUROC discrimination of
    the warning's raw value against the poor label.
    """
    triggered = [r["triggered"] for r in records]
    poor = [r["poor"] for r in records]

    tp = sum(1 for t, p in zip(triggered, poor) if t and p)
    fp = sum(1 for t, p in zip(triggered, poor) if t and not p)
    fn = sum(1 for t, p in zip(triggered, poor) if not t and p)
    tn = sum(1 for t, p in zip(triggered, poor) if not t and not p)

    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    false_alarm_rate = fp / (fp + tn) if (fp + tn) else None

    discrimination = None
    values = [r["value"] for r in records]
    have_all_values = all(v is not None for v in values)
    if roc_auc_score is not None and have_all_values and len(set(poor)) == 2:
        direction = WARNING_DIRECTIONS.get(warning_name, 1)
        scores = [direction * v for v in values]
        try:
            discrimination = float(roc_auc_score(poor, scores))
        except ValueError:
            discrimination = None

    return {
        "warning": warning_name,
        "n_runs": len(records),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": precision,
        "recall": recall,
        "false_alarm_rate": false_alarm_rate,
        "discrimination_auroc": discrimination,
    }


def score_all_warnings(run_records):
    """
    run_records: list of {"reliability_warnings": [...], "poor": bool} — one
    entry per (dataset, sample-size level, error condition, seed) run, per
    evaluation_protocol.md Section 3 point 3 ("predefined sample-size levels,
    repeated across multiple fixed random seeds").
    Returns one score_warning() result per warning name encountered.
    """
    by_warning = {}
    for run in run_records:
        for w in run["reliability_warnings"]:
            by_warning.setdefault(w["name"], []).append({
                "triggered": w["triggered"],
                "value": w["value"],
                "poor": run["poor"],
            })

    return [score_warning(name, records) for name, records in by_warning.items()]
