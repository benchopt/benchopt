import pandas as pd

from . import read_results


def merge_results(result_filenames, overwrite=False):
    """Merge parquet files containing results of a benchmark.

    Parameters
    ----------
    result_filenames: list of str | Path
        List of parquet files to merge.
    """
    dfs = [read_results(f) for f in result_filenames]
    df = pd.concat(dfs, ignore_index=True)
    if overwrite:
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
