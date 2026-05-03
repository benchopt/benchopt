"""Benchmarking sklearn classifiers with ``benchopt.mini``
==========================================================

This example shows how to write a complete **machine learning benchmark** in a
single Python file using the :mod:`benchopt.mini` decorator API.

We compare several scikit-learn classifiers on a binary classification task,
varying both the model family and its hyper-parameters, and report test-set
accuracy.  The whole benchmark — dataset, models and metric — fits in one
file with no directory scaffolding required.
"""

# %%
# Define the dataset
# ------------------
#
# :func:`~benchopt.mini.dataset` turns a function into a
# :class:`~benchopt.BaseDataset`.  Keyword arguments for this decorator become
# the parameter grid of the dataset (pass a list to sweep over values).
# The function body returns a ``dict`` whose keys are forwarded to every
# solver. This is equivalent to writing ``Dataset.get_data`` method.
#
# Here we generate a synthetic classification problem and split it into a
# training set and a held-out test set.  Both are returned so that each solver
# can train on the former and be evaluated on the latter.

from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

from benchopt.mini import dataset, solver, objective, get_benchmark
from benchopt.runner import run_benchmark


@dataset(n_samples=[500, 2000], random_state=0)
def classification(n_samples, random_state):
    X, y = make_classification(
        n_samples=n_samples, n_features=20, n_informative=10,
        random_state=random_state,
    )
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state
    )
    return dict(X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test)


# %%
# Define the objective
# --------------------
#
# :func:`~benchopt.mini.objective` wraps ``evaluate_result``.
#
# **Objective-driven split**: the parameter names of the decorated function
# determine what is *owned by the objective* vs. *produced by each solver*.
# Any dataset key that also appears in the evaluate signature (here ``y_test``)
# is **kept inside the objective** and never forwarded to the solver.
# Solvers therefore only receive and return what they actually need to compute.

@objective(name="Binary Classification")
def evaluate(y_pred, y_test):
    """Test accuracy (higher is better)."""
    return dict(accuracy=float((y_pred == y_test).mean()))


# %%
# Define the solvers
# ------------------
#
# :func:`~benchopt.mini.solver` wraps a function as a
# :class:`~benchopt.BaseSolver` with ``sampling_strategy = "run_once"``.
#
# Because ``y_test`` belongs to the objective, solvers receive only
# ``X_train``, ``X_test`` and ``y_train`` from the dataset — they do not
# need to pass ``y_test`` through any more.  Each solver simply returns
# ``y_pred``; the objective merges it with ``y_test`` at evaluation time.


@solver(name="Logistic Regression", C=[0.01, 0.1, 1.0, 10.0])
def logistic(X_train, X_test, y_train, C):
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression(C=C, max_iter=1000).fit(X_train, y_train)
    return dict(y_pred=clf.predict(X_test))


@solver(name="Random Forest", max_depth=[3, 5, None])
def random_forest(X_train, X_test, y_train, max_depth):
    from sklearn.ensemble import RandomForestClassifier
    clf = RandomForestClassifier(
        max_depth=max_depth, n_estimators=100, random_state=0
    ).fit(X_train, y_train)
    return dict(y_pred=clf.predict(X_test))


@solver(name="Gradient Boosting", learning_rate=[0.05, 0.1])
def gradient_boosting(X_train, X_test, y_train, learning_rate):
    from sklearn.ensemble import GradientBoostingClassifier
    clf = GradientBoostingClassifier(
        learning_rate=learning_rate, n_estimators=100, random_state=0
    ).fit(X_train, y_train)
    return dict(y_pred=clf.predict(X_test))


# %%
# Calling decorated objects directly
# -----------------------------------
#
# Every decorated class is still callable as the original function — with the
# same positional/keyword signature, no benchopt API involved.  This makes it
# easy to test individual components in isolation:

data = classification(500, 0)  # calls dataset directly
print("Dataset keys:", list(data.keys()))

result = logistic(  # calls a solver function directly
    data["X_train"], data["X_test"], data["y_train"], C=1.0
)
print("Solver result keys:", list(result.keys()))

score = evaluate(result["y_pred"], data["y_test"])  # calls evaluate directly
print(f"Quick accuracy: {score['accuracy']:.3f}")


# %%
# Collect and run
# ---------------
#
# :func:`~benchopt.mini.get_benchmark` inspects the calling module, collects
# all decorated objects and builds a :class:`~benchopt.mini.MiniBenchmark`.
#
# ``config`` sets named plot views (same format as ``config.yml``).
#
# ``run_config`` stores default kwargs for
# :func:`~benchopt.runner.run_benchmark`.  Use ``solver_names`` to restrict
# which solvers are executed — patterns are matched by substring:

bench = get_benchmark(
    config={
        "plot_configs": {
            "Accuracy (bar chart)": {"plot_kind": "bar_chart"},
        }
    },
    run_config={
        "solver_names": ["Logistic Regression", "Random Forest"],
    },
)

output_file = run_benchmark(
    bench,
    max_runs=1,       # each solver trains once (run_once strategy)
    n_repetitions=1,
    plot_result=False,  # set to True to open the HTML report in a browser
    show_progress=True,
    **bench.run_config,   # applies the solver_names filter
)


# %%
# Inspect the results
# -------------------
#
# Results are stored as a Parquet file.  We pivot the table to compare solvers
# side-by-side across dataset sizes:

import pandas as pd  # noqa: E402

df = pd.read_parquet(output_file)
pivot = (
    df[["dataset_name", "solver_name", "objective_accuracy"]]
    .pivot_table(
        index="solver_name",
        columns="dataset_name",
        values="objective_accuracy",
    )
    .sort_index()
)
print("Test accuracy per solver and dataset size")
print("=" * 55)
print(pivot.to_string(float_format="{:.3f}".format))

# %%
# Generating the HTML report
# --------------------------
#
# Set ``plot_result=True`` in :func:`~benchopt.runner.run_benchmark` to
# automatically open the interactive HTML report after the run, or call
# :func:`benchopt.plotting.plot_benchmark` on the saved Parquet file to
# generate / refresh it at any time::
#
#     from benchopt.plotting import plot_benchmark
#     plot_benchmark(output_file, bench, html=True, display=True)
#
# The ``"Accuracy (bar chart)"`` view we registered in ``config`` will appear
# in the *Available plot view* menu of the HTML page.

# %%
# Comparison with the class-based API
# ------------------------------------
#
# The mini API is a thin wrapper: each decorator generates the equivalent
# class.  The table below shows the correspondence:
#
# .. list-table::
#    :header-rows: 1
#    :widths: 30 35 35
#
#    * - Concept
#      - Class-based API
#      - ``benchopt.mini`` API
#    * - Dataset
#      - ``class Dataset(BaseDataset): get_data()``
#      - ``@dataset(**params) def fn(...)``
#    * - Solver
#      - ``class Solver(BaseSolver): set_objective / run / get_result``
#      - ``@solver(name, **params) def fn(...)``
#    * - Objective
#      - ``class Objective(BaseObjective): evaluate_result()``
#      - ``@objective(name) def fn(...)``
#    * - Run
#      - ``run_benchmark(path_to_dir)``
#      - ``run_benchmark(get_benchmark())``
#
# Once a benchmark grows beyond a few hundred lines it is straightforward to
# migrate to the full directory layout — the generated classes are identical to
# what you would write by hand.
