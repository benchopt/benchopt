import pytest
import pandas as pd

from benchopt.plotting.default_plots import ObjectiveCurvePlot


def _make_df(idx_rep=0, n_steps=5, objective_column='objective_value',
             objective_fn=None, stop_vals=None):
    """Helper: build a single-repetition results DataFrame."""
    if objective_fn is None:
        objective_fn = lambda sv: float(idx_rep + sv)  # noqa
    if stop_vals is None:
        stop_vals = list(range(n_steps))
    rows = [
        {
            'dataset_name': 'd1',
            'objective_name': 'obj1',
            'solver_name': 'solver1',
            'idx_rep': idx_rep,
            'stop_val': stop_val,
            objective_column: objective_fn(stop_val),
            'time': float(i + idx_rep + 1),
        }
        for i, stop_val in enumerate(stop_vals)
    ]
    return pd.DataFrame(rows)


@pytest.mark.parametrize(
    "strategy", ["iteration", "tolerance"],
)
def test_objective_curve_with_different_rep_lengths(strategy):
    objective_column = 'objective_test'
    max_steps = 7
    if strategy == "iteration":
        stop_vals = range(max_steps)
    else:
        stop_vals = [0.95**(max_steps - i) for i in range(max_steps)]

    df = pd.concat([
        _make_df(
            idx_rep=idx_rep,
            n_steps=n_steps,
            objective_column=objective_column,
            objective_fn=lambda sv, r=idx_rep: 42.0 + r,
            stop_vals=list(stop_vals)[:n_steps],
        )
        for idx_rep, n_steps in [(0, 3), (1, 5), (2, max_steps)]
    ], ignore_index=True)

    plot = ObjectiveCurvePlot()
    for x_axis in ['Iteration', 'Time']:
        traces = plot.plot(
            df,
            dataset='d1',
            objective='obj1',
            objective_column=objective_column,
            X_axis=x_axis,
        )

        assert len(traces) == 1
        trace = traces[0]

        if x_axis == 'Time':
            assert 'x_low' in trace
            assert 'x_high' in trace
            assert trace['x'] == [2., 3., 4., 5.5, 6.5, 8., 9.]
        else:
            # Check that all points are presents in the correct order
            assert trace['x'] == list(stop_vals)

        # Forward-filled tails keep the median constant for all iterations
        assert trace['y'] == [43.0] * max_steps


def test_objective_curve_non_numeric_column_returns_empty():
    """plot() must return [] when the objective column is non-numeric."""
    df = _make_df()
    df['objective_label'] = 'some_text'

    plot = ObjectiveCurvePlot()
    traces = plot.plot(
        df,
        dataset='d1',
        objective='obj1',
        objective_column='objective_label',
        X_axis='Iteration',
    )

    assert traces == []


def test_objective_curve_multiple_solvers_independent():
    """Each solver produces its own trace; values are independent."""
    rows = []
    for solver, base in [('A', 0.0), ('B', 100.0)]:
        for idx_rep in range(2):
            for stop_val in range(4):
                rows.append({
                    'dataset_name': 'd1',
                    'objective_name': 'obj1',
                    'solver_name': solver,
                    'idx_rep': idx_rep,
                    'stop_val': stop_val,
                    'objective_value': base + idx_rep,
                    'time': float(stop_val + 1),
                })
    df = pd.DataFrame(rows)

    plot = ObjectiveCurvePlot()
    traces = plot.plot(
        df,
        dataset='d1',
        objective='obj1',
        objective_column='objective_value',
        X_axis='Iteration',
    )

    assert len(traces) == 2
    by_label = {t['label']: t for t in traces}
    # Median of reps 0 and 1 → 0.5 and 100.5
    assert by_label['A']['y'] == [0.5] * 4
    assert by_label['B']['y'] == [100.5] * 4


def test_objective_curve_quantiles_ordered():
    """x_low must be <= x (median) <= x_high at every stop value."""
    df = pd.concat([
        _make_df(idx_rep=r, n_steps=6, objective_fn=lambda sv, r=r: float(r))
        for r in range(5)
    ], ignore_index=True)

    plot = ObjectiveCurvePlot()
    trace = plot.plot(
        df,
        dataset='d1',
        objective='obj1',
        objective_column='objective_value',
        X_axis='Time',
    )[0]

    for low, mid, high in zip(trace['x_low'], trace['x'], trace['x_high']):
        assert low <= mid <= high
