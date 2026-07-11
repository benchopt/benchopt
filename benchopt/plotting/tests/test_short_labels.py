"""Tests for benchopt.plotting.short_labels."""

import pandas as pd

from benchopt.plotting.short_labels import (
    compute_short_labels,
    compute_descriptions,
    shorten_names,
    _compute_params_info,
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


def test_all_params_constant_reduces_to_base():
    # When multiple *distinct* configurations share the same parameter values,
    # there is nothing to shorten within the group (no variation).
    # In that scenario, show just the base name.
    names = [
        "Solver[alpha=0.1,n_iter=100]",
        "Solver[alpha=0.1,n_iter=200]",
    ]
    # alpha is constant (0.1), n_iter varies → keep n_iter only
    short = compute_short_labels(names)
    assert short["Solver[alpha=0.1,n_iter=100]"] == "Solver[n_iter=100]"
    assert short["Solver[alpha=0.1,n_iter=200]"] == "Solver[n_iter=200]"


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
# _compute_params_info
# ---------------------------------------------------------------------------


def test_compute_params_info_basic():
    names = ["Solver[alpha=0.1,n_iter=100]", "Solver[alpha=0.5,n_iter=100]"]
    info = _compute_params_info(names)
    assert info["Solver[alpha=0.1,n_iter=100]"] == {
        "alpha": "0.1",
        "n_iter": "100",
    }
    assert info["Solver[alpha=0.5,n_iter=100]"] == {
        "alpha": "0.5",
        "n_iter": "100",
    }


def test_compute_params_info_no_params():
    info = _compute_params_info(["SolverA", "SolverB"])
    assert info["SolverA"] == {}
    assert info["SolverB"] == {}


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


# ---------------------------------------------------------------------------
# shorten_names
# ---------------------------------------------------------------------------


def test_shorten_names_replaces_and_keeps_full():
    df = pd.DataFrame({
        "solver_name": ["S[a=1,b=2]", "S[a=3,b=2]"],
        "dataset_name": ["d1", "d1"],
        "objective_name": ["obj1", "obj1"],
    })
    short_df, descriptions = shorten_names(df)

    # b=2 is constant → dropped; the full name moves to `*_full_name`.
    assert set(short_df["solver_name"]) == {"S[a=1]", "S[a=3]"}
    assert list(short_df["solver_full_name"]) == ["S[a=1,b=2]", "S[a=3,b=2]"]
    # Single dataset/objective → shortened to the bare base name.
    assert set(short_df["dataset_name"]) == {"d1"}

    # descriptions keyed by the short label, with the full param table.
    assert "<table>" in descriptions["S[a=1]"]
    # full params (including constant b), not only the varying ones
    assert ">b<" in descriptions["S[a=1]"]


def test_shorten_names_is_a_copy():
    df = pd.DataFrame({"solver_name": ["S[a=1]", "S[a=2]"]})
    short_df, _ = shorten_names(df)
    # Original df is untouched (short labels must never mutate the results).
    assert list(df["solver_name"]) == ["S[a=1]", "S[a=2]"]
    assert "solver_full_name" not in df.columns
    assert short_df is not df
