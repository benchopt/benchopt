import pandas as pd

from . import read_results


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
