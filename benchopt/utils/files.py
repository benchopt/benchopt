import warnings
from pathlib import Path
from itertools import takewhile

import pandas as pd

from ..config import DEBUG
from .shell_cmd import _run_shell


def rm_folder(folder):
    "Recursively delete a folder and its content."
    folder = Path(folder)
    for f in folder.iterdir():
        if f.is_dir():
            rm_folder(f)
        else:
            f.unlink()
    folder.rmdir()


def uniquify_results(file_path):
    "Add a number to filename if it already exists."
    if file_path.exists():
        parent = file_path.parent
        stem = file_path.stem
        suffix = file_path.suffix
        i = 1
        while (parent / f"{stem}_{i}{suffix}").exists():
            i += 1
        alternative = parent / f"{stem}_{i}{suffix}"
        warnings.warn(
            f"{file_path} already exists. Saving results to {alternative}"
        )
        return alternative
    else:
        return file_path


def read_results(file_path):
    """Read benchmark results as pandas DataFrame."""
    with open(file_path, "r") as f:
        metadata = {}
        for line in takewhile(lambda s: s.startswith("#"), f):
            k, v = line.split(':')
            metadata[k.strip('#')] = v.strip('\n')
        df = pd.read_csv(f, comment='#')
    return df, metadata


def write_results(df, file_path):
    """Write benchmark results to CSV file."""
    err, tag = _run_shell("git describe --tags --abbrev=0", return_output=True)
    if err != 0:
        if DEBUG:
            print(err, tag)
        tag = None
    with open(file_path, 'w') as f:
        f.write(f'# benchmark-git-tag: {tag}\n')
        df.to_csv(f)
