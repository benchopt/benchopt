from pathlib import Path


def _get_output_folder(benchmark):
    output_dir = Path(benchmark) / "outputs"
    output_dir.mkdir(exist_ok=True)
    return output_dir
