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



def generate_insights(df, stats, problem_type, readable_columns=None):
    """
    Generate smart plain English business insights
    for non-technical SME owners
    """
    # Helper function - INSIDE generate_insights
    def readable(col):
        if readable_columns and col in readable_columns:
            return readable_columns[col]
        return col.replace('_', ' ').title()
    
    insights = []

    rows = stats["overall"]["total_rows"]
    cols = stats["overall"]["total_columns"]
    cat_cols = list(stats["categorical_stats"].keys())
    num_cols = list(stats["numeric_stats"].keys())

    # Value/revenue column keywords
    value_keywords = [
        'price', 'revenue', 'sales', 'amount',
        'total', 'charges', 'cost', 'income',
        'profit', 'value', 'spend', 'payment',
        'salary', 'wage', 'fee', 'rate'
    ]

    # Find value column
    value_col = None
    for col in num_cols:
        if any(word in col.lower()
               for word in value_keywords):
            value_col = col
            break

    # If no value col found use last numeric
    if not value_col and num_cols:
        value_col = num_cols[-1]

    # Insight 1: Dataset overview
    insights.append({
        "type": "info",
        "icon": "📊",
        "text": f"Analyzing {rows:,} business records with {cols} data points each"
    })

    # Insight 2: Category vs value comparison
    if value_col and cat_cols:
        for cat_col in cat_cols:
            unique_count = stats[
                "categorical_stats"
            ][cat_col]["unique_values"]

            if 2 <= unique_count <= 8:
                try:
                    grouped = df.groupby(
                        cat_col
                    )[value_col].mean().sort_values(
                        ascending=False
                    )

                    if len(grouped) >= 2:
                        top = grouped.index[0]
                        top_val = grouped.iloc[0]
                        bot = grouped.index[-1]
                        bot_val = grouped.iloc[-1]

                        col_name = readable(value_col)
                        cat_name = readable(cat_col)

                        if bot_val > 0:
                            ratio = top_val / bot_val
                            insights.append({
                                "type": "positive",
                                "icon": "💡",
                                "text": f"'{top}' customers have {ratio:.1f}x higher average {col_name} ({top_val:,.0f}) compared to '{bot}' ({bot_val:,.0f})"
                            })
                        else:
                            insights.append({
                                "type": "positive",
                                "icon": "💡",
                                "text": f"'{top}' has the highest average {col_name} at {top_val:,.0f}"
                            })
                except:
                    pass
                break

    # Insight 3: Highest value segment
    if value_col and cat_cols:
        for cat_col in cat_cols:
            unique_count = stats[
                "categorical_stats"
            ][cat_col]["unique_values"]

            if 2 <= unique_count <= 10:
                try:
                    grouped = df.groupby(
                        cat_col
                    )[value_col].sum().sort_values(
                        ascending=False
                    )
                    top = grouped.index[0]
                    top_val = grouped.iloc[0]
                    total = grouped.sum()
                    pct = top_val / total * 100

                    col_name = value_col.replace(
                        '_', ' '
                    )
                    cat_name = cat_col.replace(
                        '_', ' '
                    )

                    insights.append({
                        "type": "positive",
                        "icon": "🏆",
                        "text": f"'{top}' is your most valuable {cat_name} group — contributing {pct:.1f}% of total {col_name} ({top_val:,.0f})"
                    })
                except:
                    pass
                break

    # Insight 4: Average and range
    if value_col:
        num_stats = stats["numeric_stats"][value_col]
        col_name = readable(value_col)
        insights.append({
            "type": "info",
            "icon": "📈",
            "text": f"Average {col_name} per record: {num_stats['mean']:,.2f} — ranging from {num_stats['min']:,.2f} to {num_stats['max']:,.2f}"
        })

    # Insight 5: Key driver correlation
    if value_col and len(num_cols) >= 2:
        try:
            num_df = df.select_dtypes(
                include=['number']
            )
            if value_col in num_df.columns:
                corr = num_df.corr()[
                    value_col
                ].drop(value_col).abs().sort_values(
                    ascending=False
                )

                if len(corr) > 0 and corr.iloc[0] > 0.2:
                    top_factor = corr.index[0]
                    col_name = value_col.replace(
                        '_', ' '
                    )
                    factor_name = readable(top_factor)
                    insights.append({
                        "type": "positive",
                        "icon": "🔗",
                        "text": f"'{factor_name}' is the strongest driver of {col_name} in your data — focus here for biggest impact"
                    })
        except:
            pass

    # Insight 6: Record count by top category
    if cat_cols:
        top_cat = cat_cols[0]
        cat_stats = stats["categorical_stats"][top_cat]
        most_common = cat_stats["most_common"]
        count = cat_stats["most_common_count"]
        pct = round(count / rows * 100, 1)
        cat_name = top_cat.replace('_', ' ')
        insights.append({
            "type": "info",
            "icon": "👥",
            "text": f"Most common {cat_name}: '{most_common}' — represents {pct}% of all your records ({count:,} records)"
        })

    # Insight 7: Data quality
    missing_total = df.isnull().sum().sum()
    if missing_total == 0:
        insights.append({
            "type": "positive",
            "icon": "✅",
            "text": "Your data is clean and complete — ready for reliable analysis"
        })
    else:
        insights.append({
            "type": "warning",
            "icon": "⚠️",
            "text": f"{missing_total:,} incomplete records were automatically filled — results may vary slightly"
        })

    # Insight 8: Outliers
    outlier_info = []
    for col in df.select_dtypes(
        include=['number']
    ).columns:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        outliers = df[
            (df[col] < Q1 - 1.5 * IQR) |
            (df[col] > Q3 + 1.5 * IQR)
        ]
        if len(outliers) > 0:
            outlier_info.append(
                f"{readable(col)} ({len(outliers)} unusual)"
            )

    if outlier_info:
        insights.append({
            "type": "warning",
            "icon": "🔍",
            "text": f"Unusual values found in: {', '.join(outlier_info[:2])} — worth reviewing manually"
        })

    # Insight 9: Problem specific action
    if problem_type == "time_series":
        insights.append({
            "type": "info",
            "icon": "📅",
            "text": "Sales trend patterns detected — upload more months of data for better forecasting accuracy"
        })
    elif problem_type == "classification":
        insights.append({
            "type": "info",
            "icon": "🎯",
            "text": "Our ML model can predict outcomes for new records — useful for risk assessment and decision making"
        })
    elif problem_type == "regression":
        insights.append({
            "type": "info",
            "icon": "📊",
            "text": "Our ML model can estimate values for new records — useful for pricing and forecasting"
        })
    elif problem_type == "clustering":
        insights.append({
            "type": "info",
            "icon": "🔵",
            "text": "Your records naturally group into segments — useful for targeted marketing and inventory planning"
        })

    return insights