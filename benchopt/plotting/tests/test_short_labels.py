"""Tests for benchopt.plotting.short_labels."""

import pandas as pd

from benchopt.plotting.short_labels import (
    compute_short_labels,
    compute_descriptions,
    shorten_names,
)


# ---------------------------------------------------------------------------
# compute_short_labels
# ---------------------------------------------------------------------------


def test_single_name_returns_base():
    # Single instance: base name only (params don't aid disambiguation).
    names = ["Solver[alpha=0.1,n_iter=100]"]
    short = compute_short_labels(names)
    assert short["Solver[alpha=0.1,n_iter=100]"] == "Solver"


def test_varying_param_only():
    names = [
        "Solver[alpha=0.1,n_iter=100]",
        "Solver[alpha=0.5,n_iter=100]",
    ]
    short = compute_short_labels(names)
    assert short["Solver[alpha=0.1,n_iter=100]"] == "Solver[alpha=0.1]"
    assert short["Solver[alpha=0.5,n_iter=100]"] == "Solver[alpha=0.5]"


def test_all_params_vary():
    names = [
        "Solver[alpha=0.1,n_iter=10]",
        "Solver[alpha=0.5,n_iter=50]",
    ]
    short = compute_short_labels(names)
    assert (
        short["Solver[alpha=0.1,n_iter=10]"] == "Solver[alpha=0.1,n_iter=10]"
    )
    assert (
        short["Solver[alpha=0.5,n_iter=50]"] == "Solver[alpha=0.5,n_iter=50]"
    )


def test_no_params():
    names = ["SolverA", "SolverB"]
    short = compute_short_labels(names)
    assert short["SolverA"] == "SolverA"
    assert short["SolverB"] == "SolverB"


def test_mixed_solver_types():
    names = [
        "SolverA[alpha=0.1,n_iter=100]",
        "SolverA[alpha=0.5,n_iter=100]",
        "SolverB[alpha=0.1]",
    ]
    short = compute_short_labels(names)
    # Within SolverA group only alpha varies
    assert short["SolverA[alpha=0.1,n_iter=100]"] == "SolverA[alpha=0.1]"
    assert short["SolverA[alpha=0.5,n_iter=100]"] == "SolverA[alpha=0.5]"
    # SolverB has only one instance – show base name only
    assert short["SolverB[alpha=0.1]"] == "SolverB"


# ---------------------------------------------------------------------------
# compute_descriptions
# ---------------------------------------------------------------------------


def test_compute_descriptions_params_table():
    desc = compute_descriptions(["S[a=1,b=2]", "S[a=3,b=2]"])
    for html in desc.values():
        assert "<table>" in html
        assert ">a<" in html
    assert ">1<" in desc["S[a=1,b=2]"]


def test_compute_descriptions_no_params_is_empty():
    desc = compute_descriptions(["SolverA", "SolverB"])
    assert desc == {"SolverA": "", "SolverB": ""}


def test_compute_descriptions_with_prose():
    # Free-text description is included even when there are no parameters.
    desc = compute_descriptions(
        ["SolverA", "S[a=1]"],
        prose={"SolverA": "A great solver", "S[a=1]": "Another one"},
    )
    assert "A great solver" in desc["SolverA"]
    assert "<table>" not in desc["SolverA"]  # no params
    assert "Another one" in desc["S[a=1]"]
    assert "<table>" in desc["S[a=1]"]       # prose + params


# ---------------------------------------------------------------------------
# shorten_names
# ---------------------------------------------------------------------------


def test_shorten_names_replaces_and_keeps_full():
    df = pd.DataFrame({
        "solver_name": ["S[a=1,b=2]", "S[a=3,b=2]"],
        "dataset_name": ["d1", "d1"],
        "objective_name": ["obj1", "obj1"],
    })
    short_df = shorten_names(df)

    # b=2 is constant → dropped; the full name moves to `*_full_name`.
    assert set(short_df["solver_name"]) == {"S[a=1]", "S[a=3]"}
    assert list(short_df["solver_full_name"]) == ["S[a=1,b=2]", "S[a=3,b=2]"]
    # Single dataset/objective → shortened to the bare base name.
    assert set(short_df["dataset_name"]) == {"d1"}

    # The description column holds the full param table, per row.
    desc = short_df["solver_description"].iloc[0]
    assert "<table>" in desc
    # full params (including constant b), not only the varying ones
    assert ">b<" in desc


def test_shorten_names_merges_solver_description():
    df = pd.DataFrame({
        "solver_name": ["S[a=1]", "S[a=2]"],
        "solver_description": ["docstring one", "docstring two"],
    })
    desc = shorten_names(df)["solver_description"].iloc[0]
    # The docstring is folded into the same hover as the params table.
    assert "docstring one" in desc
    assert "<table>" in desc


def test_shorten_names_merges_dataset_description():
    df = pd.DataFrame({
        "dataset_name": ["D[n=1]", "D[n=2]"],
        "dataset_description": ["first dataset", "second dataset"],
    })
    desc = shorten_names(df)["dataset_description"]
    assert "first dataset" in desc.iloc[0]
    assert "second dataset" in desc.iloc[1]


def test_shorten_names_is_a_copy():
    df = pd.DataFrame({"solver_name": ["S[a=1]", "S[a=2]"]})
    short_df = shorten_names(df)
    # Original df is untouched (short labels must never mutate the results).
    assert list(df["solver_name"]) == ["S[a=1]", "S[a=2]"]
    assert "solver_full_name" not in df.columns
    assert short_df is not df


def test_template_names_are_kept():
    # Names set by a parameter_template are kept, as the template already
    # sets the label, even when they look like positional options.
    names = ["S[newton-cg]", "S[lbfgs]", "T[a=1,b=2]", "T[a=3,b=2]"]
    params = {
        "S[newton-cg]": {"solver": "newton-cg"},
        "S[lbfgs]": {"solver": "lbfgs"},
        "T[a=1,b=2]": {"b": 2, "a": 1},
        "T[a=3,b=2]": {"b": 2, "a": 3},
    }
    short = compute_short_labels(names, params)
    assert short["S[newton-cg]"] == "S[newton-cg]"
    assert short["S[lbfgs]"] == "S[lbfgs]"
    assert short["T[a=1,b=2]"] == "T[a=1]"
    assert short["T[a=3,b=2]"] == "T[a=3]"


def test_template_with_key_value_is_kept():
    # A template can format the name like key=value: compare with the
    # default name from the parameters, not with the name format.
    names = ["S[a=1]", "S[a=2]"]
    params = {"S[a=1]": {"a": 1, "b": 0}, "S[a=2]": {"a": 2, "b": 1}}
    short = compute_short_labels(names, params)
    assert short == {"S[a=1]": "S[a=1]", "S[a=2]": "S[a=2]"}


def test_colliding_labels_keep_full_names():
    names = ["S[a=1,b=2]", "S[a=1,b=3]", "S[b=2]"]
    params = {
        "S[a=1,b=2]": {"a": 1, "b": 2},
        "S[a=1,b=3]": {"a": 1, "b": 3},
        "S[b=2]": {"b": 2},
    }
    short = compute_short_labels(names, params)
    # S[a=1,b=2] and S[b=2] both shorten to S[b=2]: both keep full names.
    assert short["S[a=1,b=2]"] == "S[a=1,b=2]"
    assert short["S[b=2]"] == "S[b=2]"
    assert short["S[a=1,b=3]"] == "S[b=3]"


def test_shorten_names_uses_param_columns():
    df = pd.DataFrame({
        "solver_name": ["S[newton-cg]", "S[lbfgs]", "T[n=10]", "T[n=20]"],
        # Integer parameters become floats with missing values.
        "p_solver_solver": ["newton-cg", "lbfgs", None, None],
        "p_solver_n": [float("nan"), float("nan"), 10.0, 20.0],
        "dataset_name": ["d1"] * 4,
        "objective_name": ["obj1"] * 4,
    })
    short_df = shorten_names(df)
    assert list(short_df["solver_name"]) == [
        "S[newton-cg]", "S[lbfgs]", "T[n=10]", "T[n=20]"
    ]
    # Templated names get their parameters table from the columns.
    assert "newton-cg" in short_df["solver_description"].iloc[0]
