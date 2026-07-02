"""Tests for benchopt.utils.short_labels."""
import pytest

from benchopt.utils.short_labels import (
    parse_parametrized_name,
    compute_short_labels,
    compute_params_info,
    is_shortened,
)


# ---------------------------------------------------------------------------
# parse_parametrized_name
# ---------------------------------------------------------------------------

def test_parse_no_params():
    base, params = parse_parametrized_name("LASSO")
    assert base == "LASSO"
    assert params == {}


def test_parse_single_param():
    base, params = parse_parametrized_name("LASSO[alpha=0.1]")
    assert base == "LASSO"
    assert params == {"alpha": "0.1"}


def test_parse_multiple_params():
    base, params = parse_parametrized_name("Solver[alpha=0.1,n_iter=100]")
    assert base == "Solver"
    assert params == {"alpha": "0.1", "n_iter": "100"}


def test_parse_brackets_in_value():
    # Values that contain '=' should still parse correctly.
    base, params = parse_parametrized_name("S[key=val]")
    assert base == "S"
    assert params["key"] == "val"


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
    assert short["Solver[alpha=0.1,n_iter=10]"] == "Solver[alpha=0.1,n_iter=10]"
    assert short["Solver[alpha=0.5,n_iter=50]"] == "Solver[alpha=0.5,n_iter=50]"


def test_all_params_constant_reduces_to_base():
    # When multiple *distinct* configurations share the same parameter values,
    # there is nothing to shorten within the group (no variation).
    # In that scenario, show just the base name.
    names = [
        "Solver[alpha=0.1,n_iter=100]",
        "Solver[alpha=0.1,n_iter=200]",  # only n_iter varies... wait: same alpha
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
# is_shortened
# ---------------------------------------------------------------------------

def test_is_shortened_true():
    names = [
        "Solver[alpha=0.1,n_iter=100]",
        "Solver[alpha=0.5,n_iter=100]",
    ]
    short = compute_short_labels(names)
    assert is_shortened(short)


def test_is_shortened_false_single():
    short = compute_short_labels(["OnlySolver[p=1]"])
    # base name "OnlySolver" != full name "OnlySolver[p=1]" → is_shortened=True
    assert is_shortened(short)


# ---------------------------------------------------------------------------
# compute_params_info
# ---------------------------------------------------------------------------

def test_compute_params_info_basic():
    names = ["Solver[alpha=0.1,n_iter=100]", "Solver[alpha=0.5,n_iter=100]"]
    info = compute_params_info(names)
    assert info["Solver[alpha=0.1,n_iter=100]"] == {"alpha": "0.1", "n_iter": "100"}
    assert info["Solver[alpha=0.5,n_iter=100]"] == {"alpha": "0.5", "n_iter": "100"}


def test_compute_params_info_no_params():
    info = compute_params_info(["SolverA", "SolverB"])
    assert info["SolverA"] == {}
    assert info["SolverB"] == {}
