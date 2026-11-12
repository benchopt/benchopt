import pytest
import pandas as pd

from benchopt.plotting.base import BasePlot
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


# Short names with their hover HTML, as given by `shorten_names`. "Lasso" is
# both a solver and a dataset, and "S" has an empty description.
DESC_DF = pd.DataFrame({
    'solver_name': ['Lasso', 'S'],
    'solver_description': ['solver Lasso', ''],
    'dataset_name': ['Lasso', 'D'],
    'dataset_description': ['dataset Lasso', 'dataset D'],
    'objective_name': ['O', 'O'],
    'obj_description': ['objective O', 'objective O'],
})


def test_scatter_and_options_descriptions():
    # Names get their description implicitly, solver first; an explicit
    # `description` is kept, and plots receive plain option values.
    received = []

    class Plot(BasePlot):
        name = 'scatter'
        type = 'scatter'
        options = {
            'dataset': ...,
            'ref': lambda df: [{'value': 'v', 'description': 'custom'}, 'S'],
        }

        def plot(self, df, dataset, ref):
            received.append((dataset, ref))
            return [
                {'x': [0], 'y': [0], 'label': 'Lasso'},
                {'x': [0], 'y': [0], 'label': 'S'},
                {'x': [0], 'y': [0], 'label': 'D'},
                {'x': [0], 'y': [0], 'label': 'O', 'description': None},
                {'x': [0], 'y': [0], 'label': 'x', 'description': 'custom'},
                {'x': [0], 'y': [0], 'label': 'other'},
            ]

        def get_metadata(self, df, dataset, ref):
            return {'title': 'scatter'}

    plots, options = Plot()._get_all_plots(DESC_DF)
    assert sorted(received) == [
        ('D', 'S'), ('D', 'v'), ('Lasso', 'S'), ('Lasso', 'v')
    ]
    assert options == {
        'dataset': [
            {'value': 'Lasso', 'description': 'solver Lasso'},
            {'value': 'D', 'description': 'dataset D'},
        ],
        'ref': [
            {'value': 'v', 'description': 'custom'},
            {'value': 'S', 'description': None},
        ],
    }
    traces = next(iter(plots.values()))['data']
    assert {t['label']: t['description'] for t in traces} == {
        'Lasso': 'solver Lasso', 'S': None, 'D': 'dataset D', 'O': None,
        'x': 'custom', 'other': None,
    }


def test_table_cells_descriptions():
    # String cells naming an object get its description, in any column and
    # through markup; explicit `{value, description}` cells are kept.
    custom = {'value': 'x', 'description': 'custom'}

    class Plot(BasePlot):
        name = 'table'
        type = 'table'
        options = {}

        def plot(self, df):
            return [['Lasso', 1.0], [custom, '**O**'], [3, 'other']]

        def get_metadata(self, df):
            return {'title': 'table', 'columns': ['a', 'b']}

    plots, _ = Plot()._get_all_plots(DESC_DF)
    assert next(iter(plots.values()))['data'] == [
        [{'value': 'Lasso', 'description': 'solver Lasso'}, 1.0],
        [custom, {'value': '**O**', 'description': 'objective O'}],
        [3, 'other'],
    ]
