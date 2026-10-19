"""
RQ1: automated pipeline (backend/services/automl.py, fixed n_estimators=50, no
tuning) vs. a manually tuned scikit-learn baseline. Per docs/evaluation_protocol.md
Section 3 point 2, both sides get: the same train/test split (same seed), the
same preprocessing (reused directly from automl.py's select_features/
build_preprocessor, not reimplemented separately), the same CV folds, and a
tuning budget for the manual side that is fixed and stated here before any run.

Tuning budget (design choice, stated up front — not adjusted after seeing
results): a 12-point grid over n_estimators x max_depth for a Random Forest,
searched by GridSearchCV with the same CV scheme the automated pipeline uses
for model selection. This is a fixed, small grid chosen for runtime reasons
across many datasets, not an exhaustive search — state as a scope limit in
the report, not an oversight.
"""
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, r2_score
from sklearn.model_selection import GridSearchCV, KFold, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline

from evaluation import backend_path  # noqa: F401  (side effect: adds backend/ to sys.path)
from services.automl import build_preprocessor, run_automl, select_features

RF_PARAM_GRID = {
    "model__n_estimators": [50, 100, 200],
    "model__max_depth": [None, 5, 10, 20],
}


def _cv_scheme(problem_type, y_train, seed):
    if problem_type == "classification":
        min_class = int(pd.Series(y_train).value_counts().min())
        if min_class >= 2:
            cv_folds = min(5, min_class)
            return StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed)
        return KFold(n_splits=min(5, len(y_train)), shuffle=True, random_state=seed)
    return KFold(n_splits=5, shuffle=True, random_state=seed)


def run_manual_baseline(df, problem_type, target_col, seed=42):
    """
    Same split, same preprocessing, same CV scheme as automl.run_automl's
    classification/regression paths — the only difference is GridSearchCV
    over RF_PARAM_GRID instead of picking among fixed-default candidates.
    """
    if problem_type not in ("classification", "regression"):
        return {"status": "unsupported", "performance": {}}

    X, y = select_features(df, target_col)
    if X is None or len(X.columns) == 0:
        return {"status": "error", "performance": {}}

    stratify_arg = None
    if problem_type == "classification":
        counts = pd.Series(y).value_counts()
        stratify_arg = y if counts.min() >= 2 else None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=stratify_arg
    )

    preprocessor = build_preprocessor(X_train)
    cv = _cv_scheme(problem_type, y_train, seed)

    if problem_type == "classification":
        model = RandomForestClassifier(random_state=seed)
        scoring = "accuracy"
    else:
        model = RandomForestRegressor(random_state=seed)
        scoring = "r2"

    pipeline = Pipeline([("preprocess", preprocessor), ("model", model)])
    search = GridSearchCV(pipeline, RF_PARAM_GRID, scoring=scoring, cv=cv, n_jobs=-1)
    search.fit(X_train, y_train)

    best_pipeline = search.best_estimator_
    cv_score = float(search.best_score_)

    if problem_type == "classification":
        test_score = float(accuracy_score(y_test, best_pipeline.predict(X_test)))
    else:
        test_score = float(r2_score(y_test, best_pipeline.predict(X_test)))

    return {
        "status": "success",
        "model_name": "Tuned Random Forest (GridSearchCV)",
        "best_params": search.best_params_,
        "performance": {
            "cv_score": round(cv_score, 3),
            "test_score": round(test_score, 3),
        },
    }


def _automated_scores(automated_result, problem_type):
    """Normalises automl.py's differently-named performance keys to the
    same {cv_score, test_score} shape the manual baseline uses, so the two
    sides can be compared directly."""
    perf = automated_result.get("performance", {})
    if problem_type == "classification":
        return perf.get("cv_accuracy"), perf.get("test_accuracy")
    return perf.get("cv_r2_score"), perf.get("test_r2_score")


def _majority_baseline_for_split(df, problem_type, target_col, seed):
    """
    Recomputes the same split run_automl/run_manual_baseline use internally
    (same select_features + train_test_split call, same seed -> identical
    split) purely to read off y_test's majority-class baseline, for
    warnings_eval.is_poor_performance. None for regression (not used there).
    """
    if problem_type != "classification":
        return None
    X, y = select_features(df, target_col)
    if X is None:
        return None
    counts = pd.Series(y).value_counts()
    stratify_arg = y if counts.min() >= 2 else None
    _, _, _, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=stratify_arg
    )
    return float(pd.Series(y_test).value_counts(normalize=True).max())


def run_comparison(df, problem_type, target_col, seed=42):
    """
    One (dataset, seed) comparison run. Returns both sides' results plus a
    flat `comparison` block (same-shape cv/test scores, plus the majority-
    class baseline needed by warnings_eval.is_poor_performance) for easy
    tabulation.
    """
    automated = run_automl(df.copy(), problem_type, target_col, seed=seed)
    manual = run_manual_baseline(df.copy(), problem_type, target_col, seed=seed)

    automated_cv, automated_test = _automated_scores(automated, problem_type)
    manual_perf = manual.get("performance", {})
    majority_baseline = _majority_baseline_for_split(df, problem_type, target_col, seed)

    return {
        "problem_type": problem_type,
        "target_col": target_col,
        "seed": seed,
        "automated": automated,
        "manual_baseline": manual,
        "comparison": {
            "automated_cv_score": automated_cv,
            "automated_test_score": automated_test,
            "manual_cv_score": manual_perf.get("cv_score"),
            "manual_test_score": manual_perf.get("test_score"),
            "majority_baseline": majority_baseline,
        },
    }
