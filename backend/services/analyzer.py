import pandas as pd
import numpy as np


def generate_statistics(df):
    """
    Generate comprehensive statistics
    for any dataset automatically
    """
    stats = {
        "numeric_stats": {},
        "categorical_stats": {},
        "overall": {}
    }

    # Overall stats
    stats["overall"] = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB"
    }

    # Numeric column stats
    numeric_cols = df.select_dtypes(
        include=[np.number]
    ).columns

    for col in numeric_cols:
        col_data = df[col].dropna()
        if len(col_data) > 0:
            stats["numeric_stats"][col] = {
                "mean": round(float(col_data.mean()), 2),
                "median": round(float(col_data.median()), 2),
                "min": round(float(col_data.min()), 2),
                "max": round(float(col_data.max()), 2),
                "std": round(float(col_data.std()), 2),
                "sum": round(float(col_data.sum()), 2)
            }

    # Categorical column stats
    cat_cols = df.select_dtypes(
        include=['object']
    ).columns

    for col in cat_cols:
        col_data = df[col].dropna()
        if len(col_data) > 0:
            value_counts = col_data.value_counts()
            stats["categorical_stats"][col] = {
                "unique_values": int(col_data.nunique()),
                "most_common": str(value_counts.index[0]),
                "most_common_count": int(value_counts.iloc[0]),
                "top_5": {
                    str(k): int(v)
                    for k, v in value_counts.head(5).items()
                }
            }

    return stats


def generate_insights(df, stats, problem_type):
    """
    Generate plain English business insights
    """
    insights = []

    # Insight 1: Dataset size
    rows = stats["overall"]["total_rows"]
    cols = stats["overall"]["total_columns"]
    insights.append({
        "type": "info",
        "icon": "📊",
        "text": f"Your dataset has {rows:,} records across {cols} categories"
    })

    # Insight 2: Best category insight
    for col, cat_stats in stats["categorical_stats"].items():
        if cat_stats["unique_values"] < 20:
            pct = round(
                cat_stats["most_common_count"] / rows * 100, 1
            )
            insights.append({
                "type": "positive",
                "icon": "🏆",
                "text": f"Most common {col} is '{cat_stats['most_common']}' — {pct}% of all records"
            })
            break

    # Insight 3: Revenue/cost insight
    revenue_keywords = [
        'price', 'revenue', 'sales', 'amount',
        'total', 'charges', 'cost', 'income'
    ]
    for col, num_stats in stats["numeric_stats"].items():
        if any(word in col.lower() for word in revenue_keywords):
            insights.append({
                "type": "positive",
                "icon": "💰",
                "text": f"Average {col}: {num_stats['mean']:,} | Total: {num_stats['sum']:,}"
            })
            insights.append({
                "type": "info",
                "icon": "📉",
                "text": f"{col} ranges from {num_stats['min']:,} to {num_stats['max']:,}"
            })
            break

    # Insight 4: Data quality
    missing_total = df.isnull().sum().sum()
    if missing_total == 0:
        insights.append({
            "type": "positive",
            "icon": "✅",
            "text": "Your data is complete with no missing values"
        })
    else:
        insights.append({
            "type": "warning",
            "icon": "⚠️",
            "text": f"{missing_total:,} missing values were automatically handled"
        })

    # Insight 5: Problem specific
    if problem_type == "time_series":
        insights.append({
            "type": "info",
            "icon": "📈",
            "text": "Time-based patterns detected — sales trend analysis available"
        })
    elif problem_type == "classification":
        insights.append({
            "type": "info",
            "icon": "🎯",
            "text": "Classification patterns found — prediction analysis ready"
        })
    elif problem_type == "regression":
        insights.append({
            "type": "info",
            "icon": "📊",
            "text": "Numeric patterns detected — value prediction analysis ready"
        })
    elif problem_type == "clustering":
        insights.append({
            "type": "info",
            "icon": "🔵",
            "text": "Similar record groups detected — customer segmentation available"
        })

    # Insight 6: Outlier warning
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
            outlier_cols.append(col)

    if outlier_cols:
        insights.append({
            "type": "warning",
            "icon": "🔍",
            "text": f"Unusual values detected in: {', '.join(outlier_cols[:3])}"
        })

    return insights