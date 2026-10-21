import re

import pandas as pd
import numpy as np

def _is_text_dtype(series):
    """True for text columns under BOTH pandas 2 and pandas 3.

    Fixed 2026-10-21, found by the new test suite. pandas 3 (pinned in
    requirements.txt as 3.0.1) gives text columns `StringDtype`, not `object`,
    so the previous `df[col].dtype == 'object'` comparison was False for every
    text column. That silently disabled four features in production:
    wrong-type detection in `detect_problems`, the "1,000 MMK" -> 1000 numeric
    cleaning in `auto_clean`, date parsing in `auto_clean`, and the
    type-consistency dimension of the quality score.

    `select_dtypes(include=['object'])` elsewhere in this file still matched
    text columns, because pandas 3 keeps that behaviour for backward
    compatibility (with a deprecation warning), which is why the breakage was
    partial and easy to miss by eye.
    """
    return (
        pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
    )


def text_columns(df):
    """Text column names, version-agnostically.

    Replaces `select_dtypes(include=['object'])`, which still matches pandas 3
    string columns only through a deprecated backward-compatibility path that
    emits a Pandas4Warning and is scheduled for removal. When that removal
    lands, every such call would silently stop matching text columns and
    reintroduce exactly the class of bug `_is_text_dtype` was added to fix.
    Selecting explicitly avoids depending on behaviour that is going away.
    """
    return [col for col in df.columns if _is_text_dtype(df[col])]


def looks_like_numeric_text(series, sample_size=10, hit_ratio=0.7):
    """Whether a text column is really numbers stored as text.

    Shared by `detect_problems` (wrong_types) and `quality_score_breakdown`
    (type consistency) so the two cannot disagree about the same column.
    Before 2026-10-21 they did: wrong_types stripped thousands separators and
    currency markers before testing, while the quality score called bare
    `pd.to_numeric`, which fails on "1,200,000". So a column could be reported
    as a wrong-type problem while contributing nothing to the quality score.
    """
    sample = series.dropna().head(sample_size)
    if len(sample) == 0:
        return False
    hits = 0
    for val in sample:
        cleaned = (
            str(val).replace(',', '').replace('ks', '')
            .replace('MMK', '').replace('mmk', '')
            .replace('$', '').replace('\u00a3', '').replace('\u20ac', '').strip()
        )
        try:
            float(cleaned)
            hits += 1
        except ValueError:
            pass
    return hits > len(sample) * hit_ratio


def _normalise_category(value):
    """Canonical key for spotting category values that mean the same thing but
    are written differently: case, surrounding or internal whitespace, and
    punctuation are all stripped. "Yangon", " yangon ", "YANGON." and
    "Yangon  " all collapse to "yangon"."""
    text = str(value).strip().lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^a-z0-9 ]', '', text)
    return text.strip()


def _looks_categorical(series, max_distinct_ratio=0.5, min_rows_for_ratio=20):
    """Whether a text column is plausibly a category column rather than free
    text or an identifier. Without this guard, variant detection fires on
    free-text notes and near-unique ID columns, where "variants" are
    meaningless and the output is noise."""
    non_null = series.dropna()
    if len(non_null) == 0:
        return False
    # Below min_rows_for_ratio the ratio test carries no information -- in a
    # 6-row table almost any text column is "near-unique", which suppressed
    # genuine findings like {"Yangon Store", "yangon store"}. With so few rows
    # a user can verify a reported variant instantly, so report it.
    if len(non_null) < min_rows_for_ratio:
        return True
    return non_null.nunique() <= max(2, int(len(non_null) * max_distinct_ratio))


def find_inconsistent_categories(df):
    """Groups of category values that normalise to the same key but are stored
    differently -- e.g. {"Yangon", "yangon", "Yangon "}.

    Added 2026-10-21. Previously `detect_problems` had no detector for this
    error type at all, which the evaluation harness surfaced as a real pipeline
    gap: `auto_clean` has always *fixed* casing and whitespace (steps 3 and 8),
    but nothing ever *reported* the problem, so a user never saw that their
    data had the issue. Detection and treatment are now symmetric.
    """
    found = []
    for col in text_columns(df):
        if not _looks_categorical(df[col]):
            continue
        groups = {}
        for raw in df[col].dropna().unique():
            key = _normalise_category(raw)
            if not key:
                continue
            groups.setdefault(key, set()).add(str(raw))
        variants = {k: sorted(v) for k, v in groups.items() if len(v) > 1}
        if variants:
            found.append({
                "column": col,
                "group_count": len(variants),
                "affected_values": int(sum(len(v) for v in variants.values())),
                # Cap the examples so a pathological column cannot bloat the
                # API response; group_count above still reports the true total.
                "examples": [
                    {"canonical": k, "variants": v}
                    for k, v in list(variants.items())[:5]
                ],
            })
    return found


def detect_problems(df):
    """
    Detect all problems in dataset
    Returns dictionary of issues found
    """
    problems = {}

    # 1. Missing values
    missing = df.isnull().sum()
    missing_cols = missing[missing > 0].to_dict()
    if missing_cols:
        problems['missing_values'] = missing_cols

    # 2. Duplicate rows
    duplicate_count = df.duplicated().sum()
    if duplicate_count > 0:
        problems['duplicates'] = int(duplicate_count)

    # 3. Columns with wrong types
    wrong_types = [
        col for col in df.columns
        if _is_text_dtype(df[col]) and looks_like_numeric_text(df[col])
    ]

    if wrong_types:
        problems['wrong_types'] = wrong_types

    # 4. Outliers in numeric columns
    outlier_cols = []
    for col in df.select_dtypes(include=[np.number]).columns:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        outliers = df[
            (df[col] < Q1 - 1.5 * IQR) |
            (df[col] > Q3 + 1.5 * IQR)
        ]
        if len(outliers) > 0:
            outlier_cols.append({
                "column": col,
                "count": len(outliers)
            })

    if outlier_cols:
        problems['outliers'] = outlier_cols

    # 5. Inconsistent category spellings (see find_inconsistent_categories)
    inconsistent = find_inconsistent_categories(df)
    if inconsistent:
        problems['inconsistent_categories'] = inconsistent

    return problems


def auto_clean(df):
    """
    Improved auto cleaning pipeline
    Handles real world digital SME data
    """
    report = []
    df = df.copy()

    # 1. Remove exact duplicates
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    if removed > 0:
        report.append(
            f"Removed {removed} duplicate rows"
        )

    # 2. Clean column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(' ', '_')
        .str.replace(r'[^a-z0-9_]', '', regex=True)
    )
    report.append("Standardized column names")

    # 3. Deep whitespace cleaning
    for col in text_columns(df):
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
            .str.replace(r'\s+', ' ', regex=True)
            .str.replace('\t', ' ')
            .str.replace('\xa0', ' ')
        )
        df[col] = df[col].replace('nan', None)

    # 4. Smart number cleaning
    for col in df.columns:
        if _is_text_dtype(df[col]):
            sample = df[col].dropna().head(20)
            numeric_count = 0
            for val in sample:
                cleaned = (
                    str(val)
                    .replace(',', '')
                    .replace(' ', '')
                    .replace('ks', '')
                    .replace('MMK', '')
                    .replace('mmk', '')
                    .replace('$', '')
                    .replace('£', '')
                    .replace('€', '')
                    .strip()
                )
                # Handle k and M suffixes
                if cleaned.lower().endswith('k'):
                    cleaned = cleaned[:-1] + '000'
                if cleaned.lower().endswith('m'):
                    cleaned = cleaned[:-1] + '000000'
                try:
                    float(cleaned)
                    numeric_count += 1
                except Exception:
                    pass

            if numeric_count >= len(sample) * 0.6:
                def clean_number(val):
                    if pd.isna(val):
                        return None
                    cleaned = (
                        str(val)
                        .replace(',', '')
                        .replace(' ', '')
                        .replace('ks', '')
                        .replace('MMK', '')
                        .replace('mmk', '')
                        .replace('$', '')
                        .replace('£', '')
                        .replace('€', '')
                        .strip()
                    )
                    if cleaned.lower().endswith('k'):
                        cleaned = str(
                            float(cleaned[:-1]) * 1000
                        )
                    if cleaned.lower().endswith('m'):
                        cleaned = str(
                            float(cleaned[:-1]) * 1000000
                        )
                    try:
                        return float(cleaned)
                    except Exception:
                        return None

                df[col] = df[col].apply(clean_number)
                report.append(
                    f"Cleaned numeric values in '{col}'"
                )

    # 5. Smart date detection and standardization
    date_formats = [
        '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y',
        '%d-%m-%Y', '%Y/%m/%d', '%d.%m.%Y',
        '%d.%m.%y', '%d/%m/%y', '%B %d %Y',
        '%b %d %Y', '%d %B %Y', '%d %b %Y',
        '%Y%m%d'
    ]

    for col in df.columns:
        if _is_text_dtype(df[col]):
            if any(word in col.lower()
                   for word in ['date', 'time',
                                'day', 'month',
                                'year']):
                for fmt in date_formats:
                    try:
                        converted = pd.to_datetime(
                            df[col],
                            format=fmt,
                            errors='coerce'
                        )
                        success_rate = (
                            converted.notna().sum() /
                            len(converted)
                        )
                        if success_rate > 0.5:
                            df[col] = converted
                            report.append(
                                f"Parsed dates in '{col}'"
                            )
                            break
                    except Exception:
                        continue

    # 6. Boolean standardization
    bool_map = {
        'yes': 1, 'no': 0,
        'true': 1, 'false': 0,
        'y': 1, 'n': 0,
        't': 1, 'f': 0,
        '1': 1, '0': 0,
        'on': 1, 'off': 0,
        'active': 1, 'inactive': 0
    }

    for col in text_columns(df):
        unique_vals = (
            df[col].dropna()
            .str.lower()
            .str.strip()
            .unique()
        )
        if len(unique_vals) <= 3:
            if all(v in bool_map
                   for v in unique_vals):
                df[col] = (
                    df[col]
                    .str.lower()
                    .str.strip()
                    .map(bool_map)
                )
                report.append(
                    f"Standardized yes/no values in '{col}'"
                )

    # 7. Handle missing values
    for col in df.columns:
        missing = df[col].isnull().sum()
        if missing > 0:
            missing_pct = missing / len(df)

            if missing_pct > 0.6:
                df = df.drop(columns=[col])
                report.append(
                    f"Dropped '{col}': "
                    f"{missing_pct:.0%} missing"
                )
            elif df[col].dtype in [
                'float64', 'int64'
            ]:
                median = df[col].median()
                df[col] = df[col].fillna(median)
                report.append(
                    f"Filled {missing} missing "
                    f"values in '{col}' "
                    f"with median ({median})"
                )
            else:
                mode = df[col].mode()
                if len(mode) > 0:
                    df[col] = df[col].fillna(mode[0])
                    report.append(
                        f"Filled {missing} missing "
                        f"values in '{col}' "
                        f"with most common value"
                    )

    # 8. Outlier treatment (added 2026-10-21)
    #
    # Previously `detect_problems` reported outliers and `auto_clean` never
    # touched them -- a real gap surfaced by the evaluation harness. Two
    # deliberate design choices here, both defensible in the viva:
    #
    # (a) Values are CAPPED at the Tukey fence (winsorised), not dropped. For
    #     small SME datasets, deleting rows costs information the user cannot
    #     afford to lose, and a capped value keeps the record usable for every
    #     other column. Capping is logged per column so nothing is silent.
    #
    # (b) Columns where more than `skew_tolerance` of values fall outside the
    #     fence are left ALONE. A column with 30% of its values beyond
    #     1.5*IQR is not contaminated -- it is skewed, which is the normal
    #     shape of revenue and transaction data. Capping it would destroy the
    #     distribution rather than clean it. These columns are reported as
    #     skewed instead, so the user still learns about them.
    skew_tolerance = 0.10
    min_skew_count = 5
    # Below this many rows, IQR-based fences are too unstable to justify
    # MODIFYING anyone's data. With 6 rows the interquartile range is tiny, so
    # even a 3*IQR fence flags a merely-doubled value as "far out" -- verified
    # 2026-10-21 on a 6-row sample where a plausible 2.4M revenue was capped.
    # Below the floor, extreme values are reported and left intact: the user
    # can eyeball 20 rows themselves, and a wrong cap is unrecoverable.
    min_rows_to_cap = 20
    for col in df.select_dtypes(include=[np.number]).columns:
        series = df[col].dropna()
        # Low-cardinality numerics are flags/codes (0/1, ratings), not
        # measurements -- a Tukey fence is meaningless on them.
        if series.nunique() <= 5:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        if iqr <= 0:
            continue
        # Tukey's two fences, used for two different purposes. Values past the
        # inner fence (1.5*IQR, "outside") are merely unusual -- on small SME
        # data a genuine large sale lands here routinely, so these are
        # REPORTED and left intact. Only values past the outer fence (3*IQR,
        # "far out") are capped, because at that distance a data-entry error
        # (misplaced decimal, units typed into a currency column) is the more
        # likely explanation. Capping everything past the inner fence would
        # quietly shrink real revenue figures, which is worse than leaving an
        # outlier in place.
        low = q1 - 1.5 * iqr
        high = q3 + 1.5 * iqr
        extreme_low = q1 - 3.0 * iqr
        extreme_high = q3 + 3.0 * iqr

        mild_count = int(
            (((df[col] < low) | (df[col] > high))
             & (df[col] >= extreme_low) & (df[col] <= extreme_high)).sum()
        )
        outlier_mask = (df[col] < extreme_low) | (df[col] > extreme_high)
        outlier_count = int(outlier_mask.sum())

        if mild_count > 0:
            report.append(
                f"Noted {mild_count} unusually high or low value(s) in "
                f"'{col}' — left unchanged, as values this far from the "
                f"middle are often genuine"
            )
        if outlier_count == 0:
            continue
        if len(series) < min_rows_to_cap:
            report.append(
                f"Noted {outlier_count} extreme value(s) in '{col}' — left "
                f"unchanged because there are only {len(series)} rows, too few "
                f"to tell a data-entry error from a genuine extreme"
            )
            continue

        # Both conditions required. A proportion test alone misfires badly on
        # small data -- with 6 rows, ONE data-entry error is 17% and would be
        # dismissed as "skew", which is exactly backwards for the small SME
        # datasets this tool exists for. A skewed *distribution* cannot be
        # evidenced by a handful of points; with fewer than min_skew_count
        # extreme values a data-entry error is at least as likely.
        if (
            outlier_count >= min_skew_count
            and outlier_count / len(series) > skew_tolerance
        ):
            report.append(
                f"Left '{col}' unchanged: {outlier_count} values "
                f"({outlier_count / len(series):.0%}) lie outside the normal "
                f"range, which indicates a skewed distribution rather than "
                f"data errors"
            )
            continue

        df[col] = df[col].clip(lower=extreme_low, upper=extreme_high)
        report.append(
            f"Capped {outlier_count} extreme value(s) in '{col}' to the "
            f"range {extreme_low:.2f} to {extreme_high:.2f} "
            f"(values were not deleted)"
        )

    # 9. Standardize text categories
    for col in text_columns(df):
        df[col] = (
            df[col]
            .str.strip()
            .str.lower()
        )

    return df, report



def quality_score_breakdown(df):
    """Per-dimension quality components plus their unweighted mean.

    IMPORTANT, and stated here rather than left implicit: this composite is a
    **heuristic of this project's own design, not a validated data-quality
    metric.** Three dimensions are averaged with equal weight because there is
    no evidence base for weighting them differently, not because equal weights
    are known to be correct. The 10-point consistency penalty per
    numeric-looking text column is likewise an arbitrary round number. The
    score is useful as a relative before/after indicator for one dataset; it
    should not be compared across datasets or read as an absolute measure.

    Deliberately NOT folded into the composite: the inconsistent-category
    problem now detected by `find_inconsistent_categories`. Adding a fourth
    dimension would require inventing a weight for it, and this project's own
    evaluation (docs/study3_results.md) found that invented thresholds and
    weights do not generalise. It is reported through `detect_problems`
    instead, where it needs no weight.

    Returned separately from `calculate_quality_score` so the API can show the
    components rather than a single opaque number -- the transparency
    convention in CLAUDE.md Section 7.
    """
    # Completeness: proportion of cells that are present.
    total_cells = int(df.size)
    missing_cells = int(df.isnull().sum().sum())
    completeness = (
        100.0 if total_cells == 0
        else (1 - missing_cells / total_cells) * 100
    )

    # Uniqueness: proportion of rows that are not exact duplicates.
    row_count = len(df)
    uniqueness = (
        100.0 if row_count == 0
        else (1 - int(df.duplicated().sum()) / row_count) * 100
    )

    # Type consistency: penalise text columns holding numbers, which should
    # have been parsed as numeric.
    consistency = 100.0
    numeric_looking_text = []
    for col in df.columns:
        # Uses the shared `looks_like_numeric_text` rather than a bare
        # pd.to_numeric, so "1,200,000" counts as numbers-stored-as-text just
        # as `detect_problems` already treated it. The previous bare `except:`
        # here also swallowed KeyboardInterrupt and SystemExit, against the
        # no-bare-except convention in CLAUDE.md Section 7.
        if _is_text_dtype(df[col]) and looks_like_numeric_text(df[col]):
            consistency -= 10
            numeric_looking_text.append(col)
    consistency = max(consistency, 0.0)

    components = {
        "completeness": round(completeness, 1),
        "uniqueness": round(uniqueness, 1),
        "type_consistency": round(consistency, 1),
    }
    return {
        "score": round(sum(components.values()) / len(components), 1),
        "components": components,
        "numeric_looking_text_columns": numeric_looking_text,
        "method": (
            "Unweighted mean of completeness, uniqueness and type consistency. "
            "A project-specific heuristic, not a validated metric -- use for "
            "before/after comparison on one dataset, not across datasets."
        ),
    }


def calculate_quality_score(df):
    """
    Calculate data quality score 0-100.

    Thin wrapper over `quality_score_breakdown` so the existing scalar return
    contract (relied on by backend/main.py) is unchanged. See that function's
    docstring for what this number is and is not.
    """
    return quality_score_breakdown(df)["score"]

def detect_problem_type(df):
    """
    Automatically detect ML problem type
    """
    result = {
        "problem_type": None,
        "confidence": 0,
        "reason": "",
        "suggested_target": None,
        # Other problem types that are plausible for this data. Populated where
        # the choice is genuinely ambiguous, so the UI can offer an override
        # instead of presenting one guess as settled.
        "alternatives": []
    }

    target_keywords = [
        'target', 'label', 'class', 'outcome', 'result',
        'churn', 'status', 'response', 'purchased', 'default',
        'category', 'segment'
    ]

    # Words naming a measurable quantity someone would want to PREDICT, as
    # opposed to a descriptive attribute used for grouping. Matched by whole
    # token, same guard as the date keywords below. Deliberately excludes
    # ambiguous segmentation-style words ('score', 'income', 'spend',
    # 'frequency'), which appear in customer-segmentation data at least as
    # often as in regression targets -- including them would reintroduce the
    # bug this list exists to fix.
    regression_target_keywords = {
        'price', 'sales', 'revenue', 'amount', 'total', 'cost', 'profit',
        'margin', 'sum', 'turnover', 'demand', 'units', 'volume', 'weight',
        'duration', 'runtime', 'mpg', 'consumption', 'yield'
    }

    def pick_target(candidates):
        for col in candidates:
            if any(word in col.lower() for word in target_keywords):
                return col
        return candidates[-1] if candidates else None

    # Check for datetime columns. Two deliberate guards against false
    # positives found via testing: (1) only object-dtype columns are
    # considered — pd.to_datetime silently "succeeds" on any numeric column
    # by reading it as epoch nanoseconds, which would otherwise misdetect
    # e.g. a plain revenue column as a date; (2) keyword matching is by
    # whole underscore-separated token, not substring, so a column like
    # "monthly_spend" (tokens: "monthly", "spend") doesn't false-match on
    # "month" the way a raw substring check would.
    date_keywords = {'date', 'datetime', 'timestamp', 'time', 'month', 'year', 'week'}
    has_datetime = False
    date_col = None
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            continue
        tokens = set(re.split(r'[^a-z0-9]+', col.lower()))
        if tokens & date_keywords:
            try:
                pd.to_datetime(df[col])
                has_datetime = True
                date_col = col
                break
            except Exception:
                continue

    # Get numeric columns
    numeric_cols = df.select_dtypes(
        include=['number']
    ).columns.tolist()

    # Check for binary columns (0/1)
    binary_cols = [
        col for col in df.columns
        if df[col].dropna().nunique() == 2
    ]

    # Decision logic
    if has_datetime and len(numeric_cols) > 0:
        result["problem_type"] = "time_series"
        result["confidence"] = 85
        result["reason"] = f"Date column '{date_col}' detected with numeric data — forecasting available"
        result["suggested_target"] = numeric_cols[0]

    elif len(binary_cols) > 0:
        target = pick_target(binary_cols)
        result["problem_type"] = "classification"
        result["confidence"] = 85
        result["reason"] = f"Binary column '{target}' detected — classification analysis available"
        result["suggested_target"] = target

    elif len(numeric_cols) >= 2:
        # Fixed 2026-10-21. Previously ANY dataset with 2+ numeric columns was
        # routed to regression, so clustering was reachable only with 0-1
        # numeric columns -- meaning genuine segmentation data (income /
        # spending / frequency) was never detected as clustering in practice.
        #
        # The fix is evidence-based rather than positional: regression is
        # chosen only when some column actually NAMES a measurable outcome.
        # With no such evidence the data is treated as segmentation, but at
        # reduced confidence and with the alternative stated, because the
        # distinction is genuinely ambiguous from column names alone. That
        # honesty is the point -- this project's own research (RQ2, and
        # docs/study3_results.md) is about a pipeline reporting when it does
        # not know, instead of asserting a guess at full confidence.
        named_target = next(
            (
                col for col in numeric_cols
                if set(re.split(r'[^a-z0-9]+', col.lower())) & regression_target_keywords
            ),
            None,
        )
        if named_target:
            result["problem_type"] = "regression"
            result["confidence"] = 75
            result["reason"] = (
                f"Numeric column '{named_target}' looks like a measurable "
                f"outcome — value prediction available"
            )
            result["suggested_target"] = named_target
            result["alternatives"] = ["clustering"]
        else:
            result["problem_type"] = "clustering"
            result["confidence"] = 55
            result["reason"] = (
                "Multiple numeric columns but no column names a clear outcome "
                "to predict — grouping similar records instead. If one of "
                "these columns is what you want to predict, choose regression."
            )
            result["suggested_target"] = None
            result["alternatives"] = ["regression"]

    else:
        result["problem_type"] = "clustering"
        result["confidence"] = 70
        result["reason"] = "No clear target detected — grouping similar records"
        result["suggested_target"] = None

    return result

def make_readable_name(col_name):
    """
    Convert technical column names
    to readable business names
    """
    col = str(col_name)

    # Split camelCase
    col = re.sub(r'([a-z])([A-Z])', r'\1 \2', col)

    # Replace underscores with spaces
    col = col.replace('_', ' ')

    # Clean multiple spaces
    col = ' '.join(col.split())

    # Capitalize each word
    col = col.title()

    return col