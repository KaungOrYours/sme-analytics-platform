"""
Study 2 diagnostics (docs/study2_protocol.md, PRE-REGISTERED 2026-10-21).

Adds four new diagnostics to the two Study 1 already measures. Study 1's
`evaluation/diagnostics.py` is imported and reused unchanged -- nothing here
modifies it, so Study 1's frozen results stay reproducible from the same code
that produced them.

The four new diagnostics, per docs/study2_protocol.md Section 4:

  D1 epv                 minority-class count in the outer-training partition
                         divided by post-encoding feature count p. Threshold
                         < 10. This is the quantity Peduzzi et al. (1996)
                         actually studied; Study 1's n/p (rows per feature) is
                         not, and the two disagree on 6 of the 25 datasets.

  D2 fold_contamination  mean over CV folds of the fraction of validation rows
                         whose feature vector exactly matches at least one row
                         in that fold's training split. Threshold > 0.10.
                         Targets the duplicate-induced fold leakage that
                         Study 1 identified as its dominant failure mechanism
                         and had no diagnostic for.

  D3 evalml_cov          abs(std(cv_scores) / mean(cv_scores)), threshold > 0.2.
                         EvalML's pre-PR-#2622 shipped rule, verbatim, including
                         its edge-case behaviour (False when std == 0, and False
                         when mean == 0 -- the upstream code accepts false
                         negatives there rather than risk divide-by-zero).

  D4 evalml_range        max(cv_scores) - min(cv_scores), threshold >= 0.5.
                         EvalML's current shipped rule, verbatim. Upstream
                         computes `cv_range >= threshold * allowed_range` with
                         threshold=0.5 and allowed_range taken from the
                         objective's expected_range; for AUROC that range is
                         1.0, so the comparison is against 0.5. Note `>=`, not
                         `>`, matching upstream.

D2 is a property of the data and the fold assignment only -- not of the model --
so it is identical for the automated pipeline and the manual baseline on a given
(dataset, seed, corruption) run, and is computed once per run rather than per
pipeline.

IMPORTANT (fold identity): D2 must be measured on the *same* folds the CV scores
come from, or it is measuring a different partition than the one that produced
the optimism being predicted. `cv_fold_indices` below reproduces exactly the
fold construction in `diagnostics.cv_scores_for_model` -- StratifiedKFold with
n_splits capped by the minority-class count, shuffled, seeded. If that function
ever changes, this one must change with it; the shared `_n_folds` helper exists
to make the coupling explicit rather than duplicated by eye.
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

from evaluation import backend_path  # noqa: F401
from evaluation.diagnostics import (  # noqa: F401  (re-exported for runners)
    AUTOMATED_CANDIDATES,
    manual_baseline_model,
    run_automated,
    run_manual_baseline,
    split_outer,
)

# Pre-registered thresholds (docs/study2_protocol.md Section 4). Fixed before
# any Study 2 outcome was observed. Do not tune these against results.
EPV_THRESHOLD = 10.0
FOLD_CONTAMINATION_THRESHOLD = 0.10
EVALML_COV_THRESHOLD = 0.2
EVALML_RANGE_THRESHOLD = 0.5
AUROC_ALLOWED_RANGE = 1.0  # objective.expected_range[1] - expected_range[0] for AUROC

# Study 1 thresholds, carried forward unchanged for side-by-side comparison.
NP_THRESHOLD = 10.0
SIGMA_CV_THRESHOLD = 0.10


def _n_folds(y_train, n_splits=5):
    """Fold count used by diagnostics.cv_scores_for_model. Kept in one place so
    fold_contamination provably uses the same partition as the CV scores."""
    min_class = int(pd.Series(y_train).value_counts().min())
    return min(n_splits, min_class) if min_class >= 2 else min(n_splits, len(y_train))


def cv_fold_indices(X_train, y_train, seed, n_splits=5):
    """The exact (train_idx, val_idx) pairs diagnostics.cv_scores_for_model uses."""
    folds = _n_folds(y_train, n_splits)
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    return list(cv.split(X_train, y_train))


def events_per_variable(y_train, p):
    """D1. Minority-class count / post-encoding feature count."""
    if p == 0:
        return None
    minority = int(pd.Series(y_train).value_counts().min())
    return minority / p


def fold_contamination(X_train, y_train, seed, n_splits=5):
    """D2. Mean fraction of validation rows that exactly duplicate a training
    row, over the same folds the CV scores are computed on.

    Exact feature-vector match is used rather than a distance threshold: the
    mechanism being targeted is literal row duplication (Study 1's injector
    copies rows verbatim, and natural duplication in low-cardinality discrete
    feature spaces is also exact). A near-duplicate measure would introduce a
    distance metric and a second arbitrary threshold, which the pre-registration
    deliberately avoids.
    """
    rates = []
    for train_idx, val_idx in cv_fold_indices(X_train, y_train, seed, n_splits):
        train_rows = set(map(tuple, X_train.iloc[train_idx].to_numpy()))
        val_rows = X_train.iloc[val_idx].to_numpy()
        if len(val_rows) == 0:
            continue
        hits = sum(1 for row in val_rows if tuple(row) in train_rows)
        rates.append(hits / len(val_rows))
    return float(np.mean(rates)) if rates else None


def evalml_cov(cv_scores):
    """D3. EvalML's pre-PR-#2622 coefficient-of-variation rule, verbatim.

    Upstream returns False (not-high-variance) when std == 0, and also when
    mean == 0, explicitly preferring a false negative to a divide-by-zero. That
    behaviour is reproduced rather than "improved" -- the point of D3 is to score
    the shipped rule as shipped.
    """
    scores = np.asarray(cv_scores, dtype=float)
    if scores.size < 2:
        return None
    # ddof=1, not numpy's default ddof=0. Upstream EvalML builds its fold scores
    # as a pandas Series and calls `.std()` on it, and pandas defaults to ddof=1
    # where numpy defaults to ddof=0. ddof=1 is therefore the faithful choice,
    # and it also matches Study 1's own sigma_cv (diagnostics.py uses ddof=1),
    # keeping D3 comparable to it. Flagging the ambiguity rather than picking
    # silently: with 5 folds the two differ by a factor of sqrt(5/4) ~ 1.12, so
    # near the 0.2 boundary the choice can flip a trigger.
    std = scores.std(ddof=1)
    mean = scores.mean()
    if std == 0 or mean == 0:
        return 0.0              # upstream maps both cases to not-high-variance
    return float(abs(std / mean))


def evalml_range(cv_scores):
    """D4. EvalML's current shipped rule: max - min across folds."""
    scores = np.asarray(cv_scores, dtype=float)
    if scores.size < 2:
        return None
    return float(scores.max() - scores.min())


def triggered_flags(record):
    """All six diagnostics binarised at their pre-registered thresholds.

    `record` is a per-pipeline result dict carrying n, p, sigma_cv, epv,
    fold_contamination, evalml_cov, evalml_range. A diagnostic whose input is
    None (undefined for that run) yields None rather than False, so that
    "undefined" and "did not trigger" stay distinguishable in scoring.
    """
    def _gt(value, threshold):
        return None if value is None else bool(value > threshold)

    n, p = record.get("n"), record.get("p")
    np_ratio = (n / p) if (n is not None and p) else None
    epv = record.get("epv")
    return {
        # Study 1, unchanged
        "np_lt_10": None if np_ratio is None else bool(np_ratio < NP_THRESHOLD),
        "sigma_cv_gt_0.10": _gt(record.get("sigma_cv"), SIGMA_CV_THRESHOLD),
        # Study 2
        "epv_lt_10": None if epv is None else bool(epv < EPV_THRESHOLD),
        "fold_contamination_gt_0.10": _gt(
            record.get("fold_contamination"), FOLD_CONTAMINATION_THRESHOLD
        ),
        "evalml_cov_gt_0.2": _gt(record.get("evalml_cov"), EVALML_COV_THRESHOLD),
        # upstream uses >=, not >
        "evalml_range_ge_0.5": (
            None if record.get("evalml_range") is None
            else bool(record["evalml_range"] >= EVALML_RANGE_THRESHOLD * AUROC_ALLOWED_RANGE)
        ),
    }


DIAGNOSTIC_NAMES = [
    "np_lt_10",
    "sigma_cv_gt_0.10",
    "epv_lt_10",
    "fold_contamination_gt_0.10",
    "evalml_cov_gt_0.2",
    "evalml_range_ge_0.5",
]


# ---------------------------------------------------------------------------
# Two-sided failure labels (docs/study2_protocol.md Section 6)
# ---------------------------------------------------------------------------
DELTA_G = 0.05  # carried forward unchanged from Study 1


def outcome_labels(g):
    """Three labels from the same unchanged G. poor_optimism is Study 1's label
    verbatim, so Study 1's numbers stay directly comparable."""
    return {
        "poor_optimism": bool(g > DELTA_G),
        "poor_pessimism": bool(g < -DELTA_G),
        "poor_either": bool(abs(g) > DELTA_G),
    }


LABEL_NAMES = ["poor_optimism", "poor_pessimism", "poor_either"]


# ---------------------------------------------------------------------------
# Forced-duplication stratum (docs/study2_protocol.md Section 5)
# ---------------------------------------------------------------------------
def forces_duplication(X, max_distinct_multiplier=4):
    """True when the feature space is too small to hold n distinct rows, so
    duplicate rows are arithmetically unavoidable rather than a data defect.

    Pre-registered definition: the number of distinct possible feature vectors
    (product of per-column distinct-value counts, computed on the inputs alone)
    is below `max_distinct_multiplier * n`. `mux6` (6 binary features, 64
    possible vectors, n=128) and `corral` are the motivating cases.

    The product is computed with an early exit so that wide continuous datasets
    do not overflow into a meaningless astronomical number.
    """
    n = len(X)
    ceiling = max_distinct_multiplier * n
    possible = 1
    for col in X.columns:
        possible *= int(X[col].nunique())
        if possible >= ceiling:
            return False
    return True


def measure_all(X_train, y_train, p, cv_scores, seed):
    """The four new diagnostics for one pipeline's run. `p` and `cv_scores` come
    from the Study 1 run functions so the two studies describe the same fit."""
    return {
        "epv": events_per_variable(y_train, p),
        "fold_contamination": fold_contamination(X_train, y_train, seed),
        "evalml_cov": evalml_cov(cv_scores),
        "evalml_range": evalml_range(cv_scores),
    }
