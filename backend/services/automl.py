import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge
from sklearn.tree import DecisionTreeClassifier
from sklearn.cluster import KMeans
from sklearn.metrics import accuracy_score, r2_score, mean_absolute_error
import warnings
warnings.filterwarnings('ignore')


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
        "ml_insights": []
    }

    try:
        # Skip time series for now
        if problem_type == "time_series":
            results["status"] = "time_series"
            results["ml_insights"].append(
                "Time series forecasting coming soon"
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


def prepare_features(df, target_col):
    """
    Prepare features for ML
    Handle encoding and scaling
    """
    df_ml = df.copy()

    # Remove target from features
    if target_col in df_ml.columns:
        y = df_ml[target_col]
        X = df_ml.drop(columns=[target_col])
    else:
        return None, None

    # Drop non-numeric columns that
    # cannot be encoded easily
    X = X.select_dtypes(include=[np.number])

    # Fill missing values
    X = X.fillna(X.median())

    # Encode target if categorical
    if y.dtype == 'object':
        le = LabelEncoder()
        y = le.fit_transform(y.astype(str))

    return X, y


def run_classification(df, target_col, results):
    """Run classification with multiple models"""
    try:
        X, y = prepare_features(df, target_col)

        if X is None or len(X.columns) == 0:
            results["status"] = "error"
            results["ml_insights"].append(
                "Not enough numeric features for classification"
            )
            return results

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=0.2,
            random_state=42
        )

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Try multiple models
        models = {
            "Random Forest": RandomForestClassifier(
                n_estimators=50,
                random_state=42
            ),
            "Logistic Regression": LogisticRegression(
                random_state=42,
                max_iter=200
            ),
            "Decision Tree": DecisionTreeClassifier(
                random_state=42
            ),
            "Gradient Boosting": GradientBoostingClassifier(
                n_estimators=50,
                random_state=42
            )
        }

        best_acc = 0
        best_name = None
        best_model = None

        for name, model in models.items():
            try:
                if name == "Logistic Regression":
                    model.fit(X_train_scaled, y_train)
                    acc = accuracy_score(
                        y_test,
                        model.predict(X_test_scaled)
                    )
                else:
                    model.fit(X_train, y_train)
                    acc = accuracy_score(
                        y_test,
                        model.predict(X_test)
                    )

                if acc > best_acc:
                    best_acc = acc
                    best_name = name
                    best_model = model
            except:
                continue

        if best_model is None:
            results["status"] = "error"
            results["ml_insights"].append(
                "All models failed to train"
            )
            return results

        results["model_name"] = best_name
        results["performance"] = {
            "accuracy": round(best_acc, 3)
        }

        # Feature importance
        if hasattr(best_model, 'feature_importances_'):
            importances = best_model.feature_importances_
            feature_imp = sorted(
                zip(X.columns, importances),
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
        elif hasattr(best_model, 'coef_'):
            # Logistic Regression uses coef_
            importances = abs(best_model.coef_[0])
            feature_imp = sorted(
                zip(X.columns, importances),
                key=lambda x: x[1],
                reverse=True
            )
            results["feature_importance"] = [
                {
                    "feature": f,
                    "importance": round(
                        float(imp) / max(importances), 3
                    )
                }
                for f, imp in feature_imp[:6]
            ]


        # ML Insights
        results["ml_insights"].append(
            f"Best model: {best_name}"
        )
        results["ml_insights"].append(
            f"Prediction accuracy: {best_acc * 100:.1f}%"
        )

        if best_acc > 0.8:
            results["ml_insights"].append(
                "Strong predictive patterns found ✅"
            )
        elif best_acc > 0.6:
            results["ml_insights"].append(
                "Moderate patterns — more data may improve accuracy"
            )
        else:
            results["ml_insights"].append(
                "Weak patterns — consider adding more features"
            )

        # Top feature insight
        if results["feature_importance"]:
            top = results["feature_importance"][0]
            results["ml_insights"].append(
                f"Most important factor: "
                f"'{top['feature'].replace('_', ' ')}'"
            )

    except Exception as e:
        results["status"] = "error"
        results["ml_insights"].append(
            f"Classification failed: {str(e)[:100]}"
        )

    return results


def run_regression(df, target_col, results):
    """Run regression with multiple models"""
    try:
        X, y = prepare_features(df, target_col)

        if X is None or len(X.columns) == 0:
            results["status"] = "error"
            results["ml_insights"].append(
                "Not enough numeric features for regression"
            )
            return results

        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=0.2,
            random_state=42
        )

        models = {
            "Random Forest": RandomForestRegressor(
                n_estimators=50,
                random_state=42
            ),
            "Linear Regression": LinearRegression(),
            "Ridge Regression": Ridge(alpha=1.0)
        }

        best_r2 = -999
        best_name = None
        best_model = None

        for name, model in models.items():
            try:
                model.fit(X_train, y_train)
                r2 = r2_score(
                    y_test,
                    model.predict(X_test)
                )
                if r2 > best_r2:
                    best_r2 = r2
                    best_name = name
                    best_model = model
            except:
                continue

        if best_model is None:
            results["status"] = "error"
            return results

        mae = mean_absolute_error(
            y_test,
            best_model.predict(X_test)
        )

        results["model_name"] = best_name
        results["performance"] = {
            "r2_score": round(max(best_r2, 0), 3),
            "mae": round(float(mae), 2)
        }

        # Feature importance
        if hasattr(best_model, 'feature_importances_'):
            importances = best_model.feature_importances_
            feature_imp = sorted(
                zip(X.columns, importances),
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
            f"Best model: {best_name}"
        )
        results["ml_insights"].append(
            f"Prediction accuracy (R²): {best_r2 * 100:.1f}%"
        )
        results["ml_insights"].append(
            f"Average prediction error (MAE): {mae:.2f}"
        )

        if best_r2 > 0.8:
            results["ml_insights"].append(
                "Excellent prediction accuracy ✅"
            )
        elif best_r2 > 0.5:
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
                f"Strongest predictor: "
                f"'{top['feature'].replace('_', ' ')}'"
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
        ).fillna(0)

        if df_num.shape[1] < 2:
            results["status"] = "insufficient_features"
            results["ml_insights"].append(
                "Need 2+ numeric columns for clustering"
            )
            return results

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(df_num)

        # Find best number of clusters
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