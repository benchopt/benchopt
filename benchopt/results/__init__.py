import pandas as pd
from pathlib import Path

from .files_utils import uniquify_fname
from ..utils.terminal_output import TerminalOutput


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
    elif path.suffix == '.csv':
        df = pd.read_csv(path)
    else:
        raise ValueError(
            f"Unsupported file format: {path.suffix}. "
            "Only .parquet and .csv files are supported."
        )
    if "data_name" in df.columns:
        df = df.rename(columns={"data_name": "dataset_name"})
    return df


def save_results(df, path):
    """Save a DataFrame in a fila at the given path.

    This function detect the format automatically based on the extension
    of the given path, defaulting to parquet if not provided.

    Parameters
    ----------
    df: pd.DataFrame
        DataFrame containing the results of the benchmark.
    path: str | Path
        Path to the parquet file to write.
    """
    terminal = TerminalOutput()

    path = Path(path)
    if path.suffix == "":
        path = path.with_suffix(".parquet")
    path = uniquify_fname(path)
    if path.suffix == '.parquet':
        try:
            df.to_parquet(path, index=False)
            terminal.savefile_status(path)
            return path
        except Exception:
            import warnings
            warnings.warn(
                f"Failed to save results in parquet format at {path}. "
                "Falling back to csv format."
            )
            path = path.with_suffix('.csv')
    if path.suffix == '.csv':
        df.to_csv(path, index=False)
        terminal.savefile_status(path)
        return path

    raise ValueError(
        f"Unsupported file format: {path.suffix}. "
        "Only .parquet and .csv files are supported."
    )
