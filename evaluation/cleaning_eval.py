"""
SUPERSEDED (2026-10-19): built for the pre-approval research design, which had
a cleaning-detection evaluation axis. The approved PDM plan (shared with this
session 2026-10-19, see docs/evaluation_protocol.md's "READ THIS FIRST" note)
does not include this axis in the formal RQ1-RQ3 evaluation at all -- kept
here, working and documented, as a reference/future-work artifact, not as
part of the current results. docs/results_summary.md is the current results
document; this file does not feed into it.

Scores backend/services/cleaner.py's detect_problems() and auto_clean() against
the ground truth from evaluation/injectors.py, per docs/evaluation_protocol.md
Section 3 point 1: detection precision/recall and reconstruction accuracy,
per error type, kept separate (not combined into one corruption-rate dial).

Important, deliberately-surfaced finding baked into this module rather than
hidden: detect_problems() only returns a *count* for missing_values/outliers
(not row identity) and has no detector at all for inconsistent_categories.
Where the production function can't answer a cell-level question, this module
says so in the result's "notes" field instead of inventing an answer.
"""
import re

import numpy as np
import pandas as pd

from evaluation import backend_path  # noqa: F401  (side effect: adds backend/ to sys.path)
from services.cleaner import detect_problems, auto_clean


def _cleaned_column_name(col):
    """
    Mirrors auto_clean()'s step 2 column-renaming exactly (strip, lowercase,
    spaces -> underscores, strip anything outside a-z0-9_) so reconstruction
    scoring can find the right column in auto_clean's output. Keep this in
    sync with cleaner.py if that renaming logic ever changes.
    """
    col = str(col).strip().lower().replace(" ", "_")
    return re.sub(r"[^a-z0-9_]", "", col)


def _iqr_outlier_cells(df, columns):
    """
    Replicates detect_problems()'s exact IQR rule (Q1/Q3 quantiles, 1.5xIQR
    fences) but at cell level, since the production function only returns a
    per-column count. If cleaner.py's outlier formula changes, this must be
    kept in sync with it — it is a proxy for "what the detector would flag,"
    not an independent definition.
    """
    flagged = set()
    for col in columns:
        if col not in df.columns:
            continue
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        mask = (df[col] < lower) | (df[col] > upper)
        for idx in df.index[mask.fillna(False)]:
            flagged.add((idx, col))
    return flagged


def _precision_recall(predicted, actual):
    predicted, actual = set(predicted), set(actual)
    tp = len(predicted & actual)
    precision = tp / len(predicted) if predicted else None
    recall = tp / len(actual) if actual else None
    return precision, recall, tp, len(predicted), len(actual)


def score_detection(error_type, corrupted_df, ground_truth):
    """
    Returns {precision, recall, true_positives, predicted_count,
    actual_count, notes}. `notes` records any gap between what's asked and
    what the production detector can actually answer.
    """
    problems = detect_problems(corrupted_df)

    if error_type == "missing_values":
        predicted = {(idx, col) for col in corrupted_df.columns
                     for idx in corrupted_df.index[corrupted_df[col].isna()]}
        actual = set(ground_truth["cells"])
        precision, recall, tp, n_pred, n_actual = _precision_recall(predicted, actual)
        note = (
            "detect_problems' missing-value check is an exact isnull().sum() count, "
            "not a learned/heuristic detector — any precision < 1 here means the "
            "dataset already had nulls before injection, not a detector mistake."
        )

    elif error_type == "duplicates":
        predicted_mask = corrupted_df.duplicated(keep="first")
        predicted = set(corrupted_df.index[predicted_mask])
        actual = set(ground_truth["duplicate_row_indices"])
        precision, recall, tp, n_pred, n_actual = _precision_recall(predicted, actual)
        note = (
            "duplicated() is exact-match detection — these are injected exact "
            "copies, so this measures whether the mechanism works, not whether "
            "near-duplicates would be caught (they would not be, by design)."
        )

    elif error_type == "outliers":
        corrupted_cols = {col for _, col in ground_truth["cells"]}
        predicted = _iqr_outlier_cells(corrupted_df, corrupted_cols)
        actual = set(ground_truth["cells"])
        precision, recall, tp, n_pred, n_actual = _precision_recall(predicted, actual)
        note = (
            "cell identity recovered by replicating detect_problems' IQR formula "
            "(it only returns a per-column count in production) — keep this in "
            "sync with cleaner.py if that formula changes."
        )

    elif error_type == "inconsistent_categories":
        # No corresponding key in detect_problems' output at all.
        predicted = set()
        actual = set(ground_truth["cells"])
        precision = None
        recall = 0.0 if actual else None
        tp, n_pred, n_actual = 0, 0, len(actual)
        note = (
            "detect_problems() has no inconsistent-category detector — recall is "
            "0 by construction, not because the detector tried and failed. This "
            "is a genuine pipeline gap worth reporting, not a scoring artifact."
        )

    else:
        raise ValueError(f"Unknown error_type: {error_type}")

    return {
        "error_type": error_type,
        "precision": precision,
        "recall": recall,
        "true_positives": tp,
        "predicted_count": n_pred,
        "actual_count": n_actual,
        "raw_detect_problems_output": problems,
        "notes": note,
    }


def score_reconstruction(error_type, corrupted_df, ground_truth):
    """
    Runs auto_clean() on the corrupted dataframe and compares its output at
    the injected positions against the true original values. Returns a
    metric appropriate to the error type (there is no single "accuracy" that
    is meaningful across all four — see notes per branch).
    """
    cleaned_df, report = auto_clean(corrupted_df)

    if error_type == "missing_values":
        numeric_errors, categorical_correct, categorical_total = [], 0, 0
        unresolved = 0
        for (idx, col), original in ground_truth["original_values"].items():
            cleaned_col = _cleaned_column_name(col)
            if cleaned_col not in cleaned_df.columns or idx not in cleaned_df.index:
                unresolved += 1
                continue
            filled = cleaned_df.at[idx, cleaned_col]
            if pd.isna(filled):
                unresolved += 1
                continue
            if isinstance(original, (int, float, np.integer, np.floating)):
                numeric_errors.append(abs(float(filled) - float(original)))
            else:
                categorical_total += 1
                if str(filled).strip().lower() == str(original).strip().lower():
                    categorical_correct += 1
        result = {
            "error_type": error_type,
            "unresolved_still_null": unresolved,
            "numeric_mean_absolute_error": (
                round(float(np.mean(numeric_errors)), 4) if numeric_errors else None
            ),
            "categorical_exact_match_rate": (
                round(categorical_correct / categorical_total, 3) if categorical_total else None
            ),
            "notes": (
                "Median/mode imputation is not expected to exactly recover the true "
                "value for numeric columns — MAE is the honest metric there; exact-match "
                "is reported only for categorical mode-fill."
            ),
        }

    elif error_type == "duplicates":
        expected_removed = len(ground_truth["duplicate_row_indices"])
        actual_removed = len(corrupted_df) - len(cleaned_df)
        result = {
            "error_type": error_type,
            "rows_before_clean": len(corrupted_df),
            "rows_after_clean": len(cleaned_df),
            "expected_rows_removed": expected_removed,
            "actual_rows_removed": actual_removed,
            "removal_matches_injection": actual_removed == expected_removed,
            "notes": "auto_clean uses exact drop_duplicates(); mismatch would mean it removed rows beyond (or short of) the injected copies.",
        }

    elif error_type == "inconsistent_categories":
        correct, total = 0, 0
        unresolved = 0
        for (idx, col), original in ground_truth["original_values"].items():
            cleaned_col = _cleaned_column_name(col)
            if cleaned_col not in cleaned_df.columns or idx not in cleaned_df.index:
                unresolved += 1
                continue
            total += 1
            cleaned_value = cleaned_df.at[idx, cleaned_col]
            if str(cleaned_value).strip().lower() == str(original).strip().lower():
                correct += 1
        result = {
            "error_type": error_type,
            "collapsed_to_canonical_rate": round(correct / total, 3) if total else None,
            "unresolved_rows": unresolved,
            "notes": (
                "auto_clean only lowercases+strips (step 8) — case and leading/trailing "
                "whitespace perturbations should collapse correctly; the whitespace-removal "
                "perturbation (e.g. 'New York' -> 'NewYork') should NOT, since that's a token "
                "merge, not a case/whitespace fix. A collapse rate well below 1.0 is therefore "
                "expected, not a bug — report it as a pipeline limitation, not a failure."
            ),
        }

    elif error_type == "outliers":
        unchanged = 0
        total = 0
        for (idx, col), original in ground_truth["original_values"].items():
            cleaned_col = _cleaned_column_name(col)
            if cleaned_col not in cleaned_df.columns or idx not in cleaned_df.index:
                continue
            total += 1
            corrupted_value = corrupted_df.at[idx, col]
            cleaned_value = cleaned_df.at[idx, cleaned_col]
            if np.isclose(cleaned_value, corrupted_value, equal_nan=True):
                unchanged += 1
        result = {
            "error_type": error_type,
            "fraction_left_unchanged_by_clean": round(unchanged / total, 3) if total else None,
            "notes": (
                "auto_clean has no outlier-treatment step at all (detect_problems flags "
                "outliers but auto_clean never caps/removes/winsorizes them) — expect this "
                "fraction to be 1.0. That is a real, reportable pipeline gap, not a test bug."
            ),
        }

    else:
        raise ValueError(f"Unknown error_type: {error_type}")

    result["auto_clean_report"] = report
    return result


def run_cleaning_evaluation(clean_df, error_type, rate, seed, injector_kwargs=None):
    """
    One full cycle for one (error_type, rate, seed): inject -> score detection
    -> score reconstruction. Returns a flat dict ready to append to a results
    table (see evaluation/run_experiment.py).
    """
    from evaluation.injectors import INJECTORS

    injector = INJECTORS[error_type]
    corrupted_df, ground_truth = injector(clean_df, rate, seed, **(injector_kwargs or {}))

    detection = score_detection(error_type, corrupted_df, ground_truth)
    reconstruction = score_reconstruction(error_type, corrupted_df, ground_truth)

    return {
        "error_type": error_type,
        "rate": rate,
        "seed": seed,
        "detection": detection,
        "reconstruction": reconstruction,
    }
