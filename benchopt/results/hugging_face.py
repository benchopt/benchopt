import tempfile
from pathlib import Path
from requests.exceptions import HTTPError

try:
    from huggingface_hub import HfApi, hf_hub_download
    from huggingface_hub.errors import (
        EntryNotFoundError, RepositoryNotFoundError, LocalTokenNotFoundError,
    )
except ImportError as e:
    raise ImportError(
        "The huggingface_hub package is required to publish to Hugging Face."
        "\n\nInstall it with: pip install huggingface_hub"
    ) from e


def publish_result_file(benchmark, file_path, repo, token=None, keep='last'):
    """Upload and merge a result file to a Hugging Face dataset repo.

    If a file for this benchmark already exists in the repo, it is downloaded,
    merged with the new results, and re-uploaded. By default (keep='last'),
    only the newest row is kept per unique configuration.

    Parameters
    ----------
    benchmark : Benchmark
        The benchmark object, used to derive the target filename.
    file_path : str | Path
        Path to the local result file to upload.
    repo : str
        Hugging Face dataset repo id, e.g. 'my-org/benchopt-results'.
    token : str | None
        HF token. If None, falls back to HF_TOKEN env var or
        huggingface-cli cached login.
    keep : str (default: 'last')
        If 'last', keep only the newest row per unique configuration on merge.
        If 'all', keep all rows (including duplicates).
    """

    # Checks in publish ensures that the file already exists,
    # so we can safely open it here.
    file_to_upload = Path(file_path)

    # Stable filename in the HF repo, derived from benchmark name (not the
    # local run filename), so all users' results for the same benchmark
    # always target the same file and get correctly merged.
    target_filename = f"{benchmark.name}.csv"

    # HfApi auto-detects auth: token arg → HF_TOKEN env var → hf-cli login
    # Check that the connection is possible.
    api = HfApi(token=token)
    try:
        api.whoami()
    except LocalTokenNotFoundError:
        raise RuntimeError(
            "Could not find the token value to connect to HF.\n\n"
            "Please go to https://huggingface.co/settings/tokens to "
            "generate a personal token $TOKEN.\nThen, either provide it "
            "with option ``-t``, as an environment variable "
            "``BENCHOPT_HF_TOKEN``, or put it in a config file "
            "``./benchopt.yml`` as ``hf_token = $TOKEN``."
        )
    except HTTPError:
        raise RuntimeError(
            f"Invalid token {token} to connect to HF.\n\n"
            "Please verify on https://huggingface.co/settings/tokens your "
            "personal token $TOKEN."
        )

    # Ensure the dataset repo exists, and create it if not
    try:
        api.repo_info(repo_id=repo, repo_type="dataset")
    except RepositoryNotFoundError:
        print(f"Repo '{repo}' not found, creating it...")
        api.create_repo(repo_id=repo, repo_type="dataset", exist_ok=True)

    from benchopt.results import read_results, save_results
    from benchopt.results.process import merge_results

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Explicit .csv extension so save_results writes CSV format
        merged_path = tmp_path / target_filename

        try:
            existing_path = hf_hub_download(
                repo_id=repo,
                filename=target_filename,
                repo_type="dataset",
                local_dir=tmp_dir,
                token=token,
            )
            print(f"Found existing '{target_filename}' in repo, merging...")
            df = merge_results(
                [Path(existing_path), file_to_upload], keep=keep
            )
        except EntryNotFoundError:
            print(f"No existing '{target_filename}' found, uploading fresh...")
            df = read_results(file_to_upload)

        # uniquify=False since we control the temp path
        saved_path = save_results(df, merged_path, uniquify=False)

        api.upload_file(
            path_or_fileobj=saved_path,
            path_in_repo=target_filename,
            repo_id=repo,
            repo_type="dataset",
            commit_message=f"Upload benchopt results for {benchmark.name}",
        )

    print(f"Uploaded {target_filename} to "
          f"https://huggingface.co/datasets/{repo}")
