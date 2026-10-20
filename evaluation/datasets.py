"""
SUPERSEDED (2026-10-19): the approved PDM plan's dataset source is
PMLBmini/TabMini, loaded directly via the `pmlb` package's fetch_data()
inside evaluation/full_run.py and evaluation/full_run_extended.py -- not
through a loader module. See docs/datasets.md for the locked 7-dataset
manifest. This file's Wholesale customers (UCI) loader was the pre-approval
placeholder used only to prove evaluation/run_experiment.py's smoke test;
it is not part of any current result and is not used by any current script.

Dataset loaders for the evaluation harness. Only one dataset is wired up so
far: Wholesale customers (UCI), used to build and smoke-test the harness
itself before docs/datasets.md's full shortlist is locked. Add one loader
function per dataset as the shortlist firms up, and register it in DATASETS.

Downloads are cached under evaluation/data/ so repeated runs don't re-fetch.
"""
import urllib.request
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def load_wholesale_customers():
    """
    UCI Wholesale customers dataset (id 292). Verified via the UCI API on
    2026-10-19 (not asserted from memory, see docs/datasets.md): 440 rows,
    8 columns (Channel, Region, Fresh, Milk, Grocery, Frozen,
    Detergents_Paper, Delicassen), no missing values, area "Business",
    DOI 10.24432/C5030X. All-numeric except Channel/Region — has no
    categorical column suited to the inconsistent_categories injector.
    """
    cache_path = DATA_DIR / "wholesale_customers.csv"
    if not cache_path.exists():
        urllib.request.urlretrieve(
            "https://archive.ics.uci.edu/static/public/292/data.csv", cache_path
        )
    df = pd.read_csv(cache_path)
    metadata = {
        "name": "Wholesale customers",
        "source": "UCI Machine Learning Repository (id 292)",
        "url": "https://archive.ics.uci.edu/dataset/292/wholesale+customers",
        "doi": "10.24432/C5030X",
        "target_col": "Region",
        "problem_type": "classification",
        "num_instances": 440,
        "num_features": 7,
        "has_categorical_column": False,
    }
    return df, metadata


DATASETS = {
    "wholesale_customers": load_wholesale_customers,
}
