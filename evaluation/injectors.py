"""
Error injectors for the cleaning-detection evaluation (docs/evaluation_protocol.md
Section 3, point 1). Each injector corrupts a clean dataframe at a stated rate and
returns the corrupted dataframe plus a ground-truth record of exactly what was
changed, so detection precision/recall and reconstruction accuracy can be scored
against a known answer rather than guessed at.

Each of the four error types is injected separately (never combined) per the
per-component rigor Rama asked for — "distinct error types tested separately."
All four take (df, rate, seed) so a caller can loop over error type x rate x seed
uniformly.
"""
import numpy as np
import pandas as pd


def inject_missing_values(df, rate, seed, columns=None):
    """
    Null out `rate` fraction of non-null cells in each of `columns` (default:
    all columns). Ground truth: exact (row, column) positions nulled and their
    original values, for reconstruction-accuracy scoring after cleaning.
    """
    rng = np.random.default_rng(seed)
    df = df.copy()
    columns = columns if columns is not None else df.columns.tolist()

    cells = []
    original_values = {}
    for col in columns:
        non_null_idx = df.index[df[col].notna()]
        n_to_corrupt = int(round(len(non_null_idx) * rate))
        if n_to_corrupt == 0:
            continue
        chosen = rng.choice(non_null_idx, size=n_to_corrupt, replace=False)
        for idx in chosen:
            original_values[(idx, col)] = df.at[idx, col]
            df.at[idx, col] = np.nan
            cells.append((idx, col))

    ground_truth = {
        "type": "missing_values",
        "rate": rate,
        "seed": seed,
        "cells": cells,
        "original_values": original_values,
    }
    return df, ground_truth


def inject_duplicates(df, rate, seed):
    """
    Append exact copies of `rate` fraction of rows (sampled without
    replacement) to the end of the dataframe. Ground truth: which row
    positions in the *corrupted* (ignore_index=True) dataframe are the
    injected copies, and which original row each came from.

    Appending rather than shuffling keeps row identity simple: pandas
    `duplicated(keep='first')` marks the later-occurring row as the
    duplicate, which is exactly the appended copy here.
    """
    rng = np.random.default_rng(seed)
    df = df.reset_index(drop=True).copy()
    n_to_duplicate = int(round(len(df) * rate))

    if n_to_duplicate == 0:
        return df.copy(), {
            "type": "duplicates", "rate": rate, "seed": seed,
            "duplicate_row_indices": [], "source_row_indices": [],
        }

    source_idx = rng.choice(df.index, size=n_to_duplicate, replace=False)
    dup_rows = df.loc[source_idx].copy()
    corrupted = pd.concat([df, dup_rows], ignore_index=True)

    duplicate_row_indices = list(range(len(df), len(df) + n_to_duplicate))

    ground_truth = {
        "type": "duplicates",
        "rate": rate,
        "seed": seed,
        "duplicate_row_indices": duplicate_row_indices,
        "source_row_indices": [int(i) for i in source_idx],
    }
    return corrupted, ground_truth


def _perturb_category(value, rng):
    """
    One of four category-inconsistency patterns real SME data shows: case
    mismatch (both directions), stray whitespace, and collapsed/stripped
    whitespace (e.g. "New York" -> "NewYork"). A design choice, not an
    exhaustive typo model — flag as such if the report discusses it.
    """
    value = str(value)
    choice = rng.integers(0, 4)
    if choice == 0:
        return value.upper()
    elif choice == 1:
        return value.lower()
    elif choice == 2:
        return f" {value} "
    else:
        return value.replace(" ", "")


def inject_inconsistent_categories(df, rate, seed, columns=None):
    """
    Perturb `rate` fraction of non-null cells in each categorical column
    (default: all object-dtype columns) with a case/whitespace variant that
    represents the same underlying category. Ground truth: positions
    perturbed and their original (canonical) values.

    Caveat recorded here rather than discovered later: `backend/services/
    cleaner.py`'s `detect_problems` has no dedicated inconsistent-category
    detector (unlike missing/duplicates/outliers) — see
    `evaluation/cleaning_eval.py` for how that's handled honestly rather than
    papered over.
    """
    rng = np.random.default_rng(seed)
    df = df.copy()
    columns = columns if columns is not None else df.select_dtypes(include="object").columns.tolist()

    cells = []
    original_values = {}
    for col in columns:
        non_null_idx = df.index[df[col].notna()]
        n_to_corrupt = int(round(len(non_null_idx) * rate))
        if n_to_corrupt == 0:
            continue
        chosen = rng.choice(non_null_idx, size=n_to_corrupt, replace=False)
        for idx in chosen:
            original_values[(idx, col)] = df.at[idx, col]
            df.at[idx, col] = _perturb_category(df.at[idx, col], rng)
            cells.append((idx, col))

    ground_truth = {
        "type": "inconsistent_categories",
        "rate": rate,
        "seed": seed,
        "cells": cells,
        "original_values": original_values,
    }
    return df, ground_truth


def inject_outliers(df, rate, seed, columns=None, magnitude=8.0):
    """
    Push `rate` fraction of non-null cells in each numeric column (default:
    all numeric columns) `magnitude` standard deviations away from their
    original value, in a random direction. `magnitude=8.0` is a design
    choice intended to sit well outside detect_problems' 1.5xIQR rule, not a
    validated "realistic outlier" model — state as such if challenged.
    Columns with zero/undefined std (constant columns) are skipped.
    """
    rng = np.random.default_rng(seed)
    df = df.copy()
    columns = columns if columns is not None else df.select_dtypes(include=np.number).columns.tolist()

    cells = []
    original_values = {}
    for col in columns:
        std = df[col].std()
        if pd.isna(std) or std == 0:
            continue
        # Outlier shift is a float (magnitude * std); upcast int columns so
        # pandas doesn't reject or silently truncate the corrupted value.
        if pd.api.types.is_integer_dtype(df[col]):
            df[col] = df[col].astype(float)
        non_null_idx = df.index[df[col].notna()]
        n_to_corrupt = int(round(len(non_null_idx) * rate))
        if n_to_corrupt == 0:
            continue
        chosen = rng.choice(non_null_idx, size=n_to_corrupt, replace=False)
        for idx in chosen:
            original_values[(idx, col)] = df.at[idx, col]
            sign = rng.choice([-1, 1])
            df.at[idx, col] = df.at[idx, col] + sign * magnitude * std
            cells.append((idx, col))

    ground_truth = {
        "type": "outliers",
        "rate": rate,
        "seed": seed,
        "cells": cells,
        "original_values": original_values,
    }
    return df, ground_truth


INJECTORS = {
    "missing_values": inject_missing_values,
    "duplicates": inject_duplicates,
    "inconsistent_categories": inject_inconsistent_categories,
    "outliers": inject_outliers,
}
