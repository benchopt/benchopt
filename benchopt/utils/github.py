from pathlib import Path
from github import Github


BENCHOPT_RESULT_REPO = 'benchopt/results'


def list_all_files(repo):
    "List all existing files in a github repo."
    all_files = []
    contents = repo.get_contents('')
    while contents:
        file_content = contents.pop(0)
        if file_content.type == "dir":
            contents.extend(repo.get_contents(file_content.path))
        else:
            all_files.append(file_content.path)
    return all_files


def publish_result_file(benchmark_name, file_path, token):
    "Upload a result file to github for a given benchmark."

    file_to_upload = Path(file_path)
    if not file_to_upload.exists():
        raise FileNotFoundError(
            f"Could not upload file {file_to_upload}."
        )

    g = Github(login_or_token=token)
    repo = g.get_repo(BENCHOPT_RESULT_REPO)

    with file_to_upload.open('r') as f:
        file_content = f.read()

    git_dir = f'outputs/{benchmark_name}'
    git_path = f'{git_dir}/{file_to_upload.name}'
    all_files = list_all_files(repo)

    if git_path in all_files:
        prev_content = repo.get_contents(git_path)
        if prev_content.decoded_content.decode('utf-8') == file_content:
            print(f"File {git_path} is already uploaded.")
            return
        repo.update_file(git_path, f"RESULT update {git_path}",
                         file_content, sha=prev_content.sha,
                         branch="main")
    else:
        repo.create_file(git_path, f"RESULT upload {git_path}",
                         file_content, branch="main")
    print(f"Uploaded file {file_to_upload.name} in benchopt/results")
