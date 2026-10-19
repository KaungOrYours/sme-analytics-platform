"""
Core measurement code for the approved PDM plan's RQ1/RQ2/RQ3
(`docs/evaluation_protocol.md`, frozen after the pilot run via `pilot.py`).

Two diagnostics are measured per run, matching the approved plan exactly
(the earlier `suspected_leakage` warning from `automl.py` is NOT part of
this formal evaluation -- the approved plan excludes any leakage-flag
warning unless a valid literature-sourced detector is found, and the
locked literature matrix (`docs/literature_matrix.md`) found none):

- n/p: outer-training rows (n) / post-encoding feature count (p), both
  frozen before outcome observation.
- sigma_CV: standard deviation of the selected model's cross-validation
  scores across folds.

And one outcome:

- G = S_CV,selected - S_test (signed: validation-to-test *optimism* only,
  not instability in either direction). "poor" = 1[G > delta_G], with
  delta_G frozen independently of n/p and sigma_CV -- NOT tuned to the data
  in this run.

Both the automated pipeline and the manual baseline are measured on the
SAME outer train/test split and the SAME CV folds. The test partition is
never corrupted; corruption (when present) is applied only to the outer
training partition before either pipeline sees it.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from evaluation import backend_path  # noqa: F401
from services.automl import build_preprocessor

# Automated pipeline's candidate models -- same spirit as automl.py's fixed,
# no-hyperparameter-search candidate set, trimmed to what's appropriate for
# these very small (n<=500) binary-classification datasets.
AUTOMATED_CANDIDATES = {
    "Random Forest": lambda seed: RandomForestClassifier(n_estimators=50, random_state=seed),
    "Logistic Regression": lambda seed: LogisticRegression(random_state=seed, max_iter=1000),
    "Decision Tree": lambda seed: DecisionTreeClassifier(random_state=seed),
}

# Manual baseline: a single, fully prespecified model (plain logistic
# regression) -- per the approved plan's "fully prespecified ... model
# family" requirement, and matching TabMini's own observation that a plain
# logistic regression is a strong, standard baseline on small tabular data.
def manual_baseline_model(seed):
    return LogisticRegression(random_state=seed, max_iter=1000)


def post_encoding_feature_count(X_train, preprocessor):
    """p: post-encoding feature count, computed once the preprocessor is
    fit on the training fold only (never the test partition)."""
    preprocessor.fit(X_train)
    return len(preprocessor.get_feature_names_out())


def cv_scores_for_model(pipeline, X_train, y_train, seed, n_splits=5):
    """Repeated-fold-safe CV score vector for sigma_CV. n_splits capped by
    the smaller class's count so every fold has both classes."""
    min_class = int(pd.Series(y_train).value_counts().min())
    folds = min(n_splits, min_class) if min_class >= 2 else min(n_splits, len(y_train))
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    scores = []
    for train_idx, val_idx in cv.split(X_train, y_train):
        X_tr, X_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
        y_tr, y_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
        fitted = pipeline
        fitted.fit(X_tr, y_tr)
        proba = fitted.predict_proba(X_val)[:, 1]
        scores.append(roc_auc_score(y_val, proba))
    return np.array(scores)


def run_automated(X_train, y_train, X_test, y_test, seed):
    """Selects among AUTOMATED_CANDIDATES by mean CV AUROC (no
    hyperparameter search, matching the live app's automl.py philosophy),
    returns S_CV,selected, sigma_CV, S_test, and G for the selected model."""
    preprocessor = build_preprocessor(X_train)
    best_name, best_mean, best_scores = None, -1, None

    for name, make_model in AUTOMATED_CANDIDATES.items():
        pipeline = Pipeline([("preprocess", build_preprocessor(X_train)), ("model", make_model(seed))])
        scores = cv_scores_for_model(pipeline, X_train, y_train, seed)
        mean_score = scores.mean()
        if mean_score > best_mean:
            best_name, best_mean, best_scores = name, mean_score, scores

    sigma_cv = float(best_scores.std(ddof=1)) if len(best_scores) >= 2 else None

    final_pipeline = Pipeline([("preprocess", build_preprocessor(X_train)),
                                ("model", AUTOMATED_CANDIDATES[best_name](seed))])
    final_pipeline.fit(X_train, y_train)
    test_proba = final_pipeline.predict_proba(X_test)[:, 1]
    s_test = roc_auc_score(y_test, test_proba)

    return {
        "model_name": best_name,
        "s_cv_selected": float(best_mean),
        "sigma_cv": sigma_cv,
        "s_test": float(s_test),
        "G": float(best_mean - s_test),
        "n": len(X_train),
        "p": post_encoding_feature_count(X_train, preprocessor),
    }


def run_manual_baseline(X_train, y_train, X_test, y_test, seed):
    """Same CV scheme, single fully-prespecified model (logistic regression),
    no model-selection step since there is only one candidate."""
    pipeline = Pipeline([("preprocess", build_preprocessor(X_train)),
                          ("model", manual_baseline_model(seed))])
    scores = cv_scores_for_model(pipeline, X_train, y_train, seed)
    mean_score = scores.mean()
    sigma_cv = float(scores.std(ddof=1)) if len(scores) >= 2 else None

    final_pipeline = Pipeline([("preprocess", build_preprocessor(X_train)),
                                ("model", manual_baseline_model(seed))])
    final_pipeline.fit(X_train, y_train)
    test_proba = final_pipeline.predict_proba(X_test)[:, 1]
    s_test = roc_auc_score(y_test, test_proba)

    return {
        "model_name": "Logistic Regression (manual baseline)",
        "s_cv_selected": float(mean_score),
        "sigma_cv": sigma_cv,
        "s_test": float(s_test),
        "G": float(mean_score - s_test),
        "n": len(X_train),
    }


def split_outer(df, target_col, seed, test_size=0.2):
    """One outer train/test split, stratified. The test partition returned
    here must never be corrupted -- corrupt only the training half, if at
    all, after this call."""
    X = df.drop(columns=[target_col])
    y = df[target_col]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )
    return X_train.reset_index(drop=True), X_test.reset_index(drop=True), \
        y_train.reset_index(drop=True), y_test.reset_index(drop=True)
