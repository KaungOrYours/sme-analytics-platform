import pandas as pd
import numpy as np

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
    wrong_types = []
    for col in df.columns:
        if df[col].dtype == 'object':
            # Check if text column contains numbers
            sample = df[col].dropna().head(10)
            numeric_count = 0
            for val in sample:
                try:
                    # Try removing common symbols
                    clean = str(val).replace(',', '').replace('ks', '').replace('MMK', '').strip()
                    float(clean)
                    numeric_count += 1
                except:
                    pass
            if numeric_count > len(sample) * 0.7:
                wrong_types.append(col)

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
            f"✅ Removed {removed} duplicate rows"
        )

    # 2. Clean column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(' ', '_')
        .str.replace(r'[^a-z0-9_]', '', regex=True)
    )
    report.append("✅ Standardized column names")

    # 3. Deep whitespace cleaning
    for col in df.select_dtypes(include=['object']).columns:
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
        if df[col].dtype == 'object':
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
                except:
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
                    except:
                        return None

                df[col] = df[col].apply(clean_number)
                report.append(
                    f"✅ Cleaned numeric values in '{col}'"
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
        if df[col].dtype == 'object':
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
                                f"✅ Parsed dates in '{col}'"
                            )
                            break
                    except:
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

    for col in df.select_dtypes(
        include=['object']
    ).columns:
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
                    f"✅ Standardized yes/no values in '{col}'"
                )

    # 7. Handle missing values
    for col in df.columns:
        missing = df[col].isnull().sum()
        if missing > 0:
            missing_pct = missing / len(df)

            if missing_pct > 0.6:
                df = df.drop(columns=[col])
                report.append(
                    f"⚠️ Dropped '{col}': "
                    f"{missing_pct:.0%} missing"
                )
            elif df[col].dtype in [
                'float64', 'int64'
            ]:
                median = df[col].median()
                df[col] = df[col].fillna(median)
                report.append(
                    f"✅ Filled {missing} missing "
                    f"values in '{col}' "
                    f"with median ({median})"
                )
            else:
                mode = df[col].mode()
                if len(mode) > 0:
                    df[col] = df[col].fillna(mode[0])
                    report.append(
                        f"✅ Filled {missing} missing "
                        f"values in '{col}' "
                        f"with most common value"
                    )

    # 8. Standardize text categories
    for col in df.select_dtypes(
        include=['object']
    ).columns:
        df[col] = (
            df[col]
            .str.strip()
            .str.lower()
        )

    return df, report



def calculate_quality_score(df):
    """
    Calculate data quality score 0-100
    """
    scores = []

    # Completeness: no missing values
    total_cells = df.size
    missing_cells = df.isnull().sum().sum()
    completeness = (1 - missing_cells / total_cells) * 100
    scores.append(completeness)

    # Uniqueness: no duplicates
    uniqueness = (1 - df.duplicated().sum() / len(df)) * 100
    scores.append(uniqueness)

    # Consistency: proper data types
    consistency = 100
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                pd.to_numeric(df[col])
                consistency -= 10
            except:
                pass
    scores.append(max(consistency, 0))

    return round(sum(scores) / len(scores), 1)

def detect_problem_type(df):
    """
    Automatically detect ML problem type
    """
    result = {
        "problem_type": None,
        "confidence": 0,
        "reason": "",
        "suggested_target": None
    }

    # Check for datetime columns
    has_datetime = False
    date_col = None
    for col in df.columns:
        if any(word in col.lower() for word in
        ['date', 'datetime', 'timestamp',
        'time_', 'month', 'year', 'week']):
            try:
                pd.to_datetime(df[col])
                has_datetime = True
                date_col = col
                break
            except:
                continue
            has_datetime = True
            date_col = col
            break

    # Get numeric columns
    numeric_cols = df.select_dtypes(
        include=['number']
    ).columns.tolist()

    # Check for binary columns (0/1)
    binary_cols = []
    for col in df.columns:
        unique_vals = df[col].dropna().unique()
        if len(unique_vals) == 2:
            binary_cols.append(col)

    # Decision logic
    if has_datetime and len(numeric_cols) > 0:
        result["problem_type"] = "time_series"
        result["confidence"] = 85
        result["reason"] = f"Date column '{date_col}' detected with numeric data — forecasting available"
        result["suggested_target"] = numeric_cols[0]

    elif len(binary_cols) > 0:
        target = binary_cols[-1]
        result["problem_type"] = "classification"
        result["confidence"] = 85
        result["reason"] = f"Binary column '{target}' detected — classification analysis available"
        result["suggested_target"] = target

    elif len(numeric_cols) >= 2:
        target = numeric_cols[-1]
        result["problem_type"] = "regression"
        result["confidence"] = 75
        result["reason"] = f"Multiple numeric columns detected — value prediction available"
        result["suggested_target"] = target

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
    import re

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