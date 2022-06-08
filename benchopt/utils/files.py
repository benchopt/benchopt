import warnings
from pathlib import Path


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
