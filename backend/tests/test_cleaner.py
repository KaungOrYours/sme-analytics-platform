"""
Tests for backend/services/cleaner.py.

Written 2026-10-21 alongside the fixes for the four open app flaws, because
changing cleaning behaviour without tests is how the behaviour quietly drifts.
These cover the fixed cases specifically, plus the two regression bugs found by
earlier manual testing (the "monthly_spend" date false-positive and the
clustering routing) so neither can come back unnoticed.

Run from the backend directory:
    python -m pytest tests/ -v
"""
import numpy as np
import pandas as pd
import pytest

from services.cleaner import (
    auto_clean,
    calculate_quality_score,
    detect_problem_type,
    detect_problems,
    find_inconsistent_categories,
    quality_score_breakdown,
)


# ---------------------------------------------------------------------------
# Inconsistent categories: previously detected by nothing at all
# ---------------------------------------------------------------------------
def test_detects_case_and_whitespace_variants():
    df = pd.DataFrame({"city": ["Yangon", "yangon", " Yangon ", "Mandalay"] * 5})
    found = find_inconsistent_categories(df)
    assert len(found) == 1
    assert found[0]["column"] == "city"
    assert found[0]["group_count"] == 1
    variants = found[0]["examples"][0]["variants"]
    assert {"Yangon", "yangon", " Yangon "} == set(variants)


def test_detects_punctuation_variants():
    df = pd.DataFrame({"status": ["Paid.", "paid", "PAID", "Unpaid"] * 4})
    found = find_inconsistent_categories(df)
    assert found and found[0]["column"] == "status"


def test_consistent_categories_are_not_flagged():
    df = pd.DataFrame({"city": ["yangon", "mandalay", "bago"] * 6})
    assert find_inconsistent_categories(df) == []


def test_free_text_column_is_skipped():
    """Near-unique text is free text or an ID; "variants" there are noise."""
    df = pd.DataFrame({"note": [f"customer comment number {i}" for i in range(40)]})
    assert find_inconsistent_categories(df) == []


def test_inconsistent_categories_surface_in_detect_problems():
    df = pd.DataFrame({"city": ["Yangon", "yangon", "Mandalay"] * 5})
    problems = detect_problems(df)
    assert "inconsistent_categories" in problems


# ---------------------------------------------------------------------------
# Outlier treatment: previously detected but never acted on
# ---------------------------------------------------------------------------
def test_extreme_value_is_capped_not_deleted():
    values = list(range(1, 41)) + [100000]
    df = pd.DataFrame({"revenue": values})
    cleaned, report = auto_clean(df)

    assert len(cleaned) == len(df), "rows must be preserved, not dropped"
    assert cleaned["revenue"].max() < 100000, "the extreme value must be capped"
    assert any("Capped" in line for line in report), "capping must be logged"


def test_skewed_column_is_left_alone_and_reported():
    """A column where many values sit beyond the fence is skewed, not
    contaminated -- capping it would destroy the distribution."""
    rng = np.random.default_rng(0)
    skewed = np.exp(rng.normal(0, 2.5, 300))
    df = pd.DataFrame({"revenue": skewed})
    cleaned, report = auto_clean(df)

    assert cleaned["revenue"].max() == pytest.approx(skewed.max())
    assert any("Left 'revenue' unchanged" in line for line in report)


def test_binary_flag_column_is_not_capped():
    df = pd.DataFrame({"is_member": [0, 1] * 50, "spend": list(range(100))})
    cleaned, report = auto_clean(df)
    assert set(cleaned["is_member"].unique()) == {0, 1}
    assert not any("is_member" in line and "Capped" in line for line in report)


def test_constant_column_does_not_crash():
    """IQR of zero must be skipped rather than producing a degenerate fence."""
    df = pd.DataFrame({"flat": [7.0] * 30, "x": list(range(30))})
    cleaned, _ = auto_clean(df)
    assert cleaned["flat"].nunique() == 1


# ---------------------------------------------------------------------------
# Quality score
# ---------------------------------------------------------------------------
def test_perfect_data_scores_100():
    df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [5.0, 6.0, 7.0, 8.0]})
    assert calculate_quality_score(df) == 100.0


def test_missing_values_reduce_completeness_only():
    df = pd.DataFrame({"a": [1, None, 3, 4], "b": [1.0, 2.0, 3.0, 4.0]})
    detail = quality_score_breakdown(df)
    assert detail["components"]["completeness"] < 100
    assert detail["components"]["uniqueness"] == 100
    assert detail["components"]["type_consistency"] == 100


def test_duplicates_reduce_uniqueness():
    df = pd.DataFrame({"a": [1, 1, 1, 2]})
    assert quality_score_breakdown(df)["components"]["uniqueness"] < 100


def test_numeric_text_column_penalises_consistency():
    df = pd.DataFrame({"amount": ["1", "2", "3", "4"]})
    detail = quality_score_breakdown(df)
    assert detail["components"]["type_consistency"] == 90
    assert detail["numeric_looking_text_columns"] == ["amount"]


def test_genuine_text_column_does_not_penalise_consistency():
    """The narrowed except must still treat real text as fine -- this is the
    path the previous bare `except:` was covering."""
    df = pd.DataFrame({"city": ["yangon", "mandalay", "bago", "taunggyi"]})
    assert quality_score_breakdown(df)["components"]["type_consistency"] == 100


def test_empty_dataframe_does_not_divide_by_zero():
    detail = quality_score_breakdown(pd.DataFrame())
    assert detail["score"] == 100.0


def test_scalar_wrapper_matches_breakdown():
    df = pd.DataFrame({"a": [1, None, 2, 2]})
    assert calculate_quality_score(df) == quality_score_breakdown(df)["score"]


# ---------------------------------------------------------------------------
# Problem-type detection, including both previously-found bugs
# ---------------------------------------------------------------------------
def test_binary_target_gives_classification():
    df = pd.DataFrame({"age": range(20), "churn": [0, 1] * 10})
    out = detect_problem_type(df)
    assert out["problem_type"] == "classification"
    assert out["suggested_target"] == "churn"


def test_named_outcome_gives_regression():
    df = pd.DataFrame({
        "area": range(30), "bedrooms": [2, 3, 4] * 10,
        "price": [x * 1000 for x in range(30)],
    })
    out = detect_problem_type(df)
    assert out["problem_type"] == "regression"
    assert out["suggested_target"] == "price"


def test_segmentation_data_gives_clustering_with_stated_alternative():
    """The flaw fixed 2026-10-21: this previously always returned regression,
    because any 2+ numeric columns hit the regression branch positionally."""
    df = pd.DataFrame({
        "income": range(40),
        "spending_score": [x % 100 for x in range(40)],
        "visit_frequency": [x % 7 for x in range(40)],
    })
    out = detect_problem_type(df)
    assert out["problem_type"] == "clustering"
    assert out["suggested_target"] is None
    assert "regression" in out["alternatives"]
    assert out["confidence"] < 70, "ambiguous routing must not claim high confidence"


def test_numeric_column_named_like_a_date_is_not_time_series():
    """Regression test for the bug where 'monthly_spend' substring-matched
    'month' and pd.to_datetime read the numbers as epoch nanoseconds."""
    df = pd.DataFrame({
        "monthly_spend": [100.0 * i for i in range(30)],
        "total_sales": [50.0 * i for i in range(30)],
    })
    out = detect_problem_type(df)
    assert out["problem_type"] != "time_series"


def test_genuine_date_column_gives_time_series():
    df = pd.DataFrame({
        "order_date": pd.date_range("2024-01-01", periods=30).astype(str),
        "sales": [100.0 * i for i in range(30)],
    })
    out = detect_problem_type(df)
    assert out["problem_type"] == "time_series"


def test_alternatives_key_always_present():
    """The frontend may read it unconditionally."""
    for df in (
        pd.DataFrame({"a": range(10), "churn": [0, 1] * 5}),
        pd.DataFrame({"only": range(10)}),
    ):
        assert "alternatives" in detect_problem_type(df)


# ---------------------------------------------------------------------------
# Added after end-to-end testing exposed two further defects (2026-10-21)
# ---------------------------------------------------------------------------
def test_single_outlier_is_capped_not_dismissed_as_skew():
    """The skew guard must not dismiss ONE data-entry error as "skew" just
    because it is a large proportion of a modest dataset. With 25 rows a single
    outlier is 4%, but the guard previously used a proportion test alone, and
    `min_skew_count` now also requires several extreme values before a column
    is called skewed rather than contaminated.

    Note this asserts capping at 25 rows, above `min_rows_to_cap`. Below that
    floor the deliberate policy is to report and NOT modify -- see
    test_tiny_dataset_values_are_reported_not_modified. These two tests encode
    the boundary between the two behaviours.
    """
    df = pd.DataFrame({"units": list(range(8, 33)) + [9999]})
    cleaned, report = auto_clean(df)
    assert cleaned["units"].max() < 9999
    assert any("Capped" in line for line in report)


def test_currency_formatted_text_is_flagged_consistently():
    """`detect_problems` and the quality score must agree about the same
    column. They previously disagreed on '1,200,000': wrong_types stripped
    separators, the score used bare pd.to_numeric and saw genuine text."""
    df = pd.DataFrame({"revenue_mmk": ["1,200,000", "950,000", "2,400,000", "1,100,000"]})
    problems = detect_problems(df)
    detail = quality_score_breakdown(df)
    assert problems.get("wrong_types") == ["revenue_mmk"]
    assert detail["numeric_looking_text_columns"] == ["revenue_mmk"]
    assert detail["components"]["type_consistency"] == 90


def test_genuine_text_still_not_flagged_as_numeric():
    df = pd.DataFrame({"city": ["yangon", "mandalay", "bago", "taunggyi"]})
    assert detect_problems(df).get("wrong_types") is None
    assert quality_score_breakdown(df)["numeric_looking_text_columns"] == []


def test_text_columns_matches_string_and_object_dtypes():
    """Guards the pandas 2/3 dtype fix itself."""
    from services.cleaner import text_columns
    df = pd.DataFrame({"s": ["a", "b"], "n": [1, 2]})
    df["o"] = pd.Series(["x", "y"], dtype=object)
    assert set(text_columns(df)) == {"s", "o"}


def test_tiny_dataset_values_are_reported_not_modified():
    """With very few rows, IQR fences are too unstable to justify changing
    anyone's data -- a plausible 2.4M revenue was being capped on 6 rows."""
    df = pd.DataFrame({"revenue": [1200000, 950000, 2400000, 1100000, 880000, 1050000]})
    cleaned, report = auto_clean(df)
    assert cleaned["revenue"].max() == 2400000, "small-n data must not be modified"
    assert any("too few" in line for line in report), "but it must still be reported"


def test_typo_is_still_capped_once_there_are_enough_rows():
    df = pd.DataFrame({"units": list(range(8, 40)) + [9999]})
    cleaned, report = auto_clean(df)
    assert cleaned["units"].max() < 9999
    assert any("Capped" in line for line in report)


def test_mild_outlier_is_preserved_and_reported():
    """Values between the inner (1.5*IQR) and outer (3*IQR) fences are often
    genuine, so they are reported but never modified."""
    values = list(range(10, 50)) + [78]
    df = pd.DataFrame({"sales": values})
    cleaned, report = auto_clean(df)
    assert cleaned["sales"].max() == 78
    assert any("left unchanged" in line for line in report)
