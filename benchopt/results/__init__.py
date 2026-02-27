import pandas as pd
from pathlib import Path


def read_results(path):
    """Read a benchopt's result file given a path.

    The file can be either a parquet file or a csv file.
    Column "data_name" is renamed to "dataset_name" for backward compatibility.

    Parameters
    ----------
    path: str | Path
        Path to the parquet file to read.

    Returns
    -------
    df: pd.DataFrame
        DataFrame containing the results of the benchmark.
    """
    path = Path(path)

    if path.suffix == '.parquet':
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    if "data_name" in df.columns:
        df = df.rename(columns={"data_name": "dataset_name"})
    return df
