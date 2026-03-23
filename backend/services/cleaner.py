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
    Automatically fix all data problems
    Returns cleaned DataFrame and report
    """
    report = []
    df = df.copy()

    # 1. Remove duplicates
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    if removed > 0:
        report.append(f"✅ Removed {removed} duplicate rows")

    # 2. Fix column names
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    report.append("✅ Standardized column names")

    # 3. Handle missing values
    for col in df.columns:
        missing = df[col].isnull().sum()
        if missing > 0:
            missing_pct = missing / len(df)

            # Drop column if too many missing
            if missing_pct > 0.6:
                df = df.drop(columns=[col])
                report.append(f"⚠️ Dropped column '{col}': {missing_pct:.0%} missing")

            # Fill numeric with median
            elif df[col].dtype in ['float64', 'int64']:
                median = df[col].median()
                df[col] = df[col].fillna(median)
                report.append(f"✅ Filled {missing} missing values in '{col}' with median ({median})")

            # Fill text with mode
            else:
                mode = df[col].mode()
                if len(mode) > 0:
                    df[col] = df[col].fillna(mode[0])
                    report.append(f"✅ Filled {missing} missing values in '{col}' with most common value")

    # 4. Fix currency symbols
    for col in df.columns:
        if df[col].dtype == 'object':
            sample_val = str(df[col].dropna().iloc[0]) if len(df[col].dropna()) > 0 else ""
            if any(sym in sample_val for sym in ['ks', 'MMK', '$', '£', '€', ',']):
                try:
                    df[col] = df[col].str.replace(r'[ks$£€MMK,\s]', '', regex=True)
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    report.append(f"✅ Removed currency symbols from '{col}'")
                except:
                    pass

    # 5. Standardize text columns
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip().str.lower()
            report.append(f"✅ Standardized text in '{col}'")

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