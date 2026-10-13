import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold, KFold
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import LabelEncoder, StandardScaler, OneHotEncoder
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge
from sklearn.tree import DecisionTreeClassifier
from sklearn.cluster import KMeans
from sklearn.metrics import accuracy_score, r2_score, mean_absolute_error


def run_automl(df, problem_type, target_col):
    """
    Run AutoML using scikit-learn
    Automatically selects best model
    """
    results = {
        "status": "success",
        "problem_type": problem_type,
        "target_column": target_col,
        "model_name": None,
        "performance": {},
        "feature_importance": [],
        "all_candidate_scores": [],
        "ml_insights": []
    }

    try:
        # Time series
        if problem_type == "time_series":
            results = run_time_series(
                df, target_col, results
            )
            return results

        # Minimum rows check
        if len(df) < 100:
            results["status"] = "insufficient_data"
            results["ml_insights"].append(
                "Dataset too small for ML. Need 100+ rows."
            )
            return results

        # Sample large datasets for speed
        if len(df) > 3000:
            df = df.sample(3000, random_state=42)

        if problem_type == "classification":
            results = run_classification(
                df, target_col, results
            )
        elif problem_type == "regression":
            results = run_regression(
                df, target_col, results
            )
        elif problem_type == "clustering":
            results = run_clustering(
                df, results
            )
        else:
            results["status"] = "unsupported"

    except Exception as e:
        results["status"] = "error"
        results["ml_insights"].append(
            f"ML analysis could not complete: {str(e)[:100]}"
        )

    return results


def run_time_series(df, target_col, results):
    """
    Run time series forecasting.
    R2 is reported from a held-out backtest (fit on the first 80%,
    scored on the last 20%), not from the training fit itself.
    """
    try:
        # Find numeric target
        num_cols = df.select_dtypes(
            include=['number']
        ).columns.tolist()

        if not num_cols:
            results["status"] = "error"
            results["ml_insights"].append(
                "No numeric columns for forecasting"
            )
            return results

        # Use target or last numeric column
        if target_col and target_col in num_cols:
            forecast_col = target_col
        else:
            forecast_col = num_cols[-1]

        # Create time index
        y = df[forecast_col].dropna().values
        X = np.arange(len(y)).reshape(-1, 1)

        if len(y) < 10:
            results["status"] = "insufficient_data"
            results["ml_insights"].append(
                "Need at least 10 records for forecasting"
            )
            return results

        # Backtest: hold out the last 20% to measure honest out-of-sample accuracy
        split_at = min(max(int(len(y) * 0.8), len(y) - 5), len(y) - 1)
        X_train, X_test = X[:split_at], X[split_at:]
        y_train, y_test = y[:split_at], y[split_at:]

        backtest_model = LinearRegression()
        backtest_model.fit(X_train, y_train)
        y_pred_test = backtest_model.predict(X_test)
        ss_res = np.sum((y_test - y_pred_test) ** 2)
        ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        # Refit on the full series for the actual forward-looking forecast
        model = LinearRegression()
        model.fit(X, y)

        # Forecast next 5 periods
        future_X = np.arange(
            len(y), len(y) + 5
        ).reshape(-1, 1)
        forecast = model.predict(future_X)

        # Trend direction
        slope = model.coef_[0]
        if slope > 0:
            trend = "upward 📈"
            trend_pct = abs(slope / np.mean(y) * 100)
            trend_msg = f"growing at {trend_pct:.1f}% per period"
        elif slope < 0:
            trend = "downward 📉"
            trend_pct = abs(slope / np.mean(y) * 100)
            trend_msg = f"declining at {trend_pct:.1f}% per period"
        else:
            trend = "stable ➡️"
            trend_msg = "relatively stable over time"

        results["model_name"] = "Linear Trend Forecasting"
        results["performance"] = {
            "r2_score": round(max(r2, 0), 3),
        }
        results["feature_importance"] = []
        results["forecast"] = [
            round(float(v), 2) for v in forecast
        ]

        results["ml_insights"].append(
            f"Forecasting column: '{forecast_col}'"
        )
        results["ml_insights"].append(
            f"Overall trend is {trend} — {trend_msg}"
        )
        results["ml_insights"].append(
            f"Current average: {np.mean(y):,.2f}"
        )
        results["ml_insights"].append(
            f"Next period forecast: {forecast[0]:,.2f}"
        )
        results["ml_insights"].append(
            f"5-period forecast: {forecast[-1]:,.2f}"
        )
        results["ml_insights"].append(
            f"R2 is measured on a held-out backtest of the last {len(y_test)} points, not the training fit"
        )

        if r2 > 0.7:
            results["ml_insights"].append(
                "Strong trend pattern detected ✅"
            )
        elif r2 > 0.4:
            results["ml_insights"].append(
                "Moderate trend — some seasonal variation present"
            )
        else:
            results["ml_insights"].append(
                "Irregular pattern — consider seasonal analysis"
            )

    except Exception as e:
        results["status"] = "error"
        results["ml_insights"].append(
            f"Forecasting failed: {str(e)[:100]}"
        )

    return results


def select_features(df, target_col):
    """
    Split a dataframe into feature matrix and target.
    No imputation or encoding happens here — that is done inside each
    model's Pipeline so it is fit on the training fold only, not on data
    that includes the test rows.
    """
    if target_col not in df.columns:
        return None, None

    y = df[target_col]
    X = df.drop(columns=[target_col])

    # Drop columns with no values at all — nothing to learn from them
    X = X.dropna(axis=1, how='all')

    if y.dtype == 'object':
        le = LabelEncoder()
        y = le.fit_transform(y.astype(str))

    return X, y


def build_preprocessor(X):
    """
    Build a leakage-safe preprocessing step: median-impute + scale numeric
    columns, most-frequent-impute + one-hot encode categorical columns.
    Fit only ever happens on the training fold via the surrounding Pipeline.
    """
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = X.select_dtypes(exclude=[np.number]).columns.tolist()

    transformers = []

    if numeric_cols:
        numeric_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler())
        ])
        transformers.append(("num", numeric_pipeline, numeric_cols))

    if categorical_cols:
        categorical_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore"))
        ])
        transformers.append(("cat", categorical_pipeline, categorical_cols))

    return ColumnTransformer(transformers)


def readable_feature_names(preprocessor):
    names = preprocessor.get_feature_names_out()
    return [n.split("__", 1)[-1] for n in names]


def run_classification(df, target_col, results):
    """
    Run classification with multiple models.
    Models are selected by cross-validated score on the training fold only
    (not by score on the held-out test set). The test set is used once,
    purely to report a final, unbiased performance number.
    """
    try:
        X, y = select_features(df, target_col)

        if X is None or len(X.columns) == 0:
            results["status"] = "error"
            results["ml_insights"].append(
                "No usable features for classification"
            )
            return results

        class_counts = pd.Series(y).value_counts()
        stratify_arg = y if class_counts.min() >= 2 else None

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=stratify_arg
        )

        preprocessor = build_preprocessor(X_train)

        candidates = {
            "Random Forest": RandomForestClassifier(
                n_estimators=50, random_state=42
            ),
            "Logistic Regression": LogisticRegression(
                random_state=42, max_iter=200
            ),
            "Decision Tree": DecisionTreeClassifier(
                random_state=42
            ),
            "Gradient Boosting": GradientBoostingClassifier(
                n_estimators=50, random_state=42
            )
        }

        min_train_class_count = int(pd.Series(y_train).value_counts().min())
        if min_train_class_count >= 2:
            cv_folds = min(5, min_train_class_count)
            cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        else:
            cv_folds = min(5, len(y_train))
            cv = KFold(n_splits=cv_folds, shuffle=True, random_state=42)

        all_scores = []
        best_cv_score = -1
        best_name = None
        best_pipeline = None

        for name, model in candidates.items():
            try:
                pipeline = Pipeline([
                    ("preprocess", preprocessor),
                    ("model", model)
                ])
                cv_scores = cross_val_score(
                    pipeline, X_train, y_train, cv=cv, scoring="accuracy"
                )
                mean_cv = float(cv_scores.mean())
                all_scores.append({
                    "model": name,
                    "cv_accuracy": round(mean_cv, 3)
                })

                if mean_cv > best_cv_score:
                    best_cv_score = mean_cv
                    best_name = name
                    best_pipeline = pipeline
            except Exception:
                continue

        if best_pipeline is None:
            results["status"] = "error"
            results["ml_insights"].append(
                "All models failed to train"
            )
            return results

        best_pipeline.fit(X_train, y_train)
        test_acc = accuracy_score(
            y_test, best_pipeline.predict(X_test)
        )

        results["model_name"] = best_name
        results["performance"] = {
            "cv_accuracy": round(best_cv_score, 3),
            "test_accuracy": round(test_acc, 3)
        }
        results["all_candidate_scores"] = sorted(
            all_scores, key=lambda r: r["cv_accuracy"], reverse=True
        )

        feature_names = readable_feature_names(
            best_pipeline.named_steps["preprocess"]
        )
        fitted_model = best_pipeline.named_steps["model"]

        importances = None
        if hasattr(fitted_model, 'feature_importances_'):
            importances = fitted_model.feature_importances_
        elif hasattr(fitted_model, 'coef_'):
            raw = np.abs(fitted_model.coef_[0])
            importances = raw / raw.max() if raw.max() > 0 else raw

        if importances is not None:
            feature_imp = sorted(
                zip(feature_names, importances),
                key=lambda x: x[1],
                reverse=True
            )
            results["feature_importance"] = [
                {
                    "feature": f,
                    "importance": round(float(imp), 3)
                }
                for f, imp in feature_imp[:6]
            ]

        results["ml_insights"].append(
            f"Best model: {best_name} (selected by {cv_folds}-fold cross-validation)"
        )
        results["ml_insights"].append(
            f"Cross-validated accuracy: {best_cv_score * 100:.1f}%"
        )
        results["ml_insights"].append(
            f"Held-out test accuracy: {test_acc * 100:.1f}%"
        )

        if best_cv_score > 0.8:
            results["ml_insights"].append(
                "Strong predictive patterns found ✅"
            )
        elif best_cv_score > 0.6:
            results["ml_insights"].append(
                "Moderate patterns — more data may improve accuracy"
            )
        else:
            results["ml_insights"].append(
                "Weak patterns — consider adding more features"
            )

        if results["feature_importance"]:
            top = results["feature_importance"][0]
            results["ml_insights"].append(
                f"Most important factor: '{top['feature']}'"
            )

    except Exception as e:
        results["status"] = "error"
        results["ml_insights"].append(
            f"Classification failed: {str(e)[:100]}"
        )

    return results


def run_regression(df, target_col, results):
    """
    Run regression with multiple models.
    Models are selected by cross-validated R2 on the training fold only.
    The test set is used once, purely to report a final, unbiased score.
    """
    try:
        X, y = select_features(df, target_col)

        if X is None or len(X.columns) == 0:
            results["status"] = "error"
            results["ml_insights"].append(
                "No usable features for regression"
            )
            return results

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        preprocessor = build_preprocessor(X_train)

        candidates = {
            "Random Forest": RandomForestRegressor(
                n_estimators=50, random_state=42
            ),
            "Linear Regression": LinearRegression(),
            "Ridge Regression": Ridge(alpha=1.0)
        }

        cv = KFold(n_splits=5, shuffle=True, random_state=42)

        all_scores = []
        best_cv_score = -np.inf
        best_name = None
        best_pipeline = None

        for name, model in candidates.items():
            try:
                pipeline = Pipeline([
                    ("preprocess", preprocessor),
                    ("model", model)
                ])
                cv_scores = cross_val_score(
                    pipeline, X_train, y_train, cv=cv, scoring="r2"
                )
                mean_cv = float(cv_scores.mean())
                all_scores.append({
                    "model": name,
                    "cv_r2": round(mean_cv, 3)
                })

                if mean_cv > best_cv_score:
                    best_cv_score = mean_cv
                    best_name = name
                    best_pipeline = pipeline
            except Exception:
                continue

        if best_pipeline is None:
            results["status"] = "error"
            results["ml_insights"].append(
                "All models failed to train"
            )
            return results

        best_pipeline.fit(X_train, y_train)
        test_pred = best_pipeline.predict(X_test)
        test_r2 = r2_score(y_test, test_pred)
        mae = mean_absolute_error(y_test, test_pred)

        results["model_name"] = best_name
        results["performance"] = {
            "cv_r2_score": round(max(best_cv_score, 0), 3),
            "test_r2_score": round(max(test_r2, 0), 3),
            "mae": round(float(mae), 2)
        }
        results["all_candidate_scores"] = sorted(
            all_scores, key=lambda r: r["cv_r2"], reverse=True
        )

        feature_names = readable_feature_names(
            best_pipeline.named_steps["preprocess"]
        )
        fitted_model = best_pipeline.named_steps["model"]

        if hasattr(fitted_model, 'feature_importances_'):
            importances = fitted_model.feature_importances_
            feature_imp = sorted(
                zip(feature_names, importances),
                key=lambda x: x[1],
                reverse=True
            )
            results["feature_importance"] = [
                {
                    "feature": f,
                    "importance": round(float(imp), 3)
                }
                for f, imp in feature_imp[:6]
            ]
        elif hasattr(fitted_model, 'coef_'):
            raw = np.abs(fitted_model.coef_)
            denom = raw.max() if raw.max() > 0 else 1
            feature_imp = sorted(
                zip(feature_names, raw / denom),
                key=lambda x: x[1],
                reverse=True
            )
            results["feature_importance"] = [
                {
                    "feature": f,
                    "importance": round(float(imp), 3)
                }
                for f, imp in feature_imp[:6]
            ]

        results["ml_insights"].append(
            f"Best model: {best_name} (selected by 5-fold cross-validation)"
        )
        results["ml_insights"].append(
            f"Cross-validated accuracy (R2): {best_cv_score * 100:.1f}%"
        )
        results["ml_insights"].append(
            f"Held-out test accuracy (R2): {test_r2 * 100:.1f}%"
        )
        results["ml_insights"].append(
            f"Average prediction error (MAE): {mae:.2f}"
        )

        if best_cv_score > 0.8:
            results["ml_insights"].append(
                "Excellent prediction accuracy ✅"
            )
        elif best_cv_score > 0.5:
            results["ml_insights"].append(
                "Good accuracy — reasonable predictions possible"
            )
        else:
            results["ml_insights"].append(
                "Limited accuracy — more features may help"
            )

        if results["feature_importance"]:
            top = results["feature_importance"][0]
            results["ml_insights"].append(
                f"Strongest predictor: '{top['feature']}'"
            )

    except Exception as e:
        results["status"] = "error"
        results["ml_insights"].append(
            f"Regression failed: {str(e)[:100]}"
        )

    return results


def run_clustering(df, results):
    """Run K-Means clustering"""
    try:
        df_num = df.select_dtypes(
            include=['number']
        )

        if df_num.shape[1] < 2:
            results["status"] = "insufficient_features"
            results["ml_insights"].append(
                "Need 2+ numeric columns for clustering"
            )
            return results

        df_num = df_num.fillna(df_num.median())

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(df_num)

        best_k = 3
        model = KMeans(
            n_clusters=best_k,
            random_state=42,
            n_init=10
        )
        labels = model.fit_predict(X_scaled)

        cluster_counts = pd.Series(
            labels
        ).value_counts().sort_index()

        results["model_name"] = "K-Means Clustering"
        results["performance"] = {
            "num_clusters": best_k
        }

        results["ml_insights"].append(
            f"Found {best_k} distinct groups in your data"
        )

        for cluster_id, count in cluster_counts.items():
            pct = round(count / len(df) * 100, 1)
            results["ml_insights"].append(
                f"Group {cluster_id + 1}: "
                f"{count} records ({pct}%)"
            )

        results["ml_insights"].append(
            "Each group represents similar records"
        )

    except Exception as e:
        results["status"] = "error"
        results["ml_insights"].append(
            f"Clustering failed: {str(e)[:100]}"
        )

    return results
