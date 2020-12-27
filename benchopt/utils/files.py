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
