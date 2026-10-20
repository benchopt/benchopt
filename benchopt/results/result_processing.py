import pandas as pd

from . import read_results, save_results


def describe_results(source):
    """Compute summary statistics for a benchopt result table.

    Parameters
    ----------
    source: str | Path | pd.DataFrame
        Either a path to a result file (read with `read_results`) or an
        already-loaded results DataFrame (e.g. from `read_results`).

    Returns
    -------
    summary: dict
        ``n_rows``, ``n_configs`` (unique objective x solver x dataset
        triplets), ``n_repetitions``, ``objectives``, ``solvers``,
        ``datasets``, ``objective_columns`` (the ``objective_<name>`` metric
        columns, e.g. ``objective_value``, ``objective_train_loss``) and
        ``run_dates``.
    """
    df = source if isinstance(source, pd.DataFrame) else read_results(source)

    return dict(
        n_rows=len(df),
        n_configs=len(
            df[['objective_name', 'solver_name', 'dataset_name']]
            .drop_duplicates()
        ),
        n_repetitions=(
            df['idx_rep'].nunique() if 'idx_rep' in df.columns else None
        ),
        objectives=sorted(df['objective_name'].unique()),
        solvers=sorted(df['solver_name'].unique()),
        datasets=sorted(df['dataset_name'].unique()),
        objective_columns=[
            c for c in df.columns
            if c.startswith('objective_') and c != 'objective_name'
        ],
        run_dates=(
            sorted(df['run_date'].unique())
            if 'run_date' in df.columns else []
        ),
    )


def merge_results(result_filenames, keep="last"):
    """Merge parquet files containing results of a benchmark.

    Parameters
    ----------
    result_filenames: list of str | Path
        List of parquet files to merge.
    """
    assert keep in ("last", "all"), "keep must be either 'last' or 'all'"

    dfs = [read_results(f) for f in result_filenames]
    df = pd.concat(dfs, ignore_index=True).sort_values("run_date")
    if keep == "last":
        # Consider that the files can contain multiple times the same
        # configuration, and only keep the last one. This is useful when
        # merging files from multiple runs where we add new methods but don't
        # want to lose the results of the already existing methods.
        df = df.drop_duplicates(
            subset=[
                "dataset_name", "objective_name", "solver_name", "idx_rep",
                "stop_val"
            ], keep="last"
        )
    return df


def merge(result_filenames, keep='last', output=None):
    """Merge result files of a benchmark

    Parameters
    ----------
    result_filenames: list of str | Path
        List of parquet files to merge
    keep: str
        Must be "last" or "all". When merged files contain multiple
        times the same configuration, controls whether to keep all
        the lines or only keep the last result per configuration.
    output: str | Path
        Path of the new parquet file
    """
    # Merge the results.
    df = merge_results(result_filenames, keep=keep)
    result_path = save_results(df, output)
    return result_path
