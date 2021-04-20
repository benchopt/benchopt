from pathlib import Path
from github import Github
from github import GithubException


BENCHOPT_RESULT_REPO = 'benchopt/results'


def get_file_content(repo, branch, git_path):
    "Get content and sha of the file if it exists else return None."
    try:
        prev_content = repo.get_contents(git_path, ref=branch)
        return prev_content.decoded_content.decode('utf-8'), prev_content.sha
    except GithubException:
        return None, None


def publish_result_file(benchmark_name, file_path, token):
    "Upload a result file to github for a given benchmark."

    # Get file to upload and content
    file_to_upload = Path(file_path)
    if not file_to_upload.exists():
        raise FileNotFoundError(
            f"Could not upload file {file_to_upload}."
        )
    with file_to_upload.open('r') as f:
        file_content = f.read()

    git_path = f"benchmarks/{benchmark_name}/outputs/{file_to_upload.name}"
    file_name = f'{benchmark_name}/{file_to_upload.name}'

    # Get github API and origin repo
    g = Github(login_or_token=token)
    origin = g.get_repo(BENCHOPT_RESULT_REPO)
    username = g.get_user().login
    has_push_rights = origin.permissions.push

    # If no push rights, get a fork of the repo and a branch with the file name
    if not has_push_rights:
        repo = origin.create_fork()
        branch = f"{username}/{benchmark_name}"
        try:
            repo.get_branch(branch)
        except GithubException:
            master_sha = origin.get_branch(origin.default_branch).commit.sha
            repo.create_git_ref(f'refs/heads/{branch}', master_sha)
    else:
        repo = origin
        branch = origin.default_branch

    # If file already exists and is the same, do nothing.
    prev_content, prev_content_sha = get_file_content(repo, branch, git_path)
    if prev_content == file_content:
        print(f"File {file_name} is already uploaded.")
        return

    # If file does not exists in the repo, create it, else update it
    if prev_content is None:
        repo.create_file(git_path, f"RESULT upload {file_name}",
                         file_content, branch=branch)
    else:
        repo.update_file(git_path, f"RESULT update {file_name}",
                         file_content, sha=prev_content_sha,
                         branch=branch)

    # If no commit right, create a pull request
    if not has_push_rights:
        head = f"{username}:{branch}"
        pulls = list(origin.get_pulls(head=head, state='open'))
        if len(pulls) != 0:
            assert len(pulls) == 1
            print(f"Updating PR on benchopt results: {pulls[0].html_url}")
        else:
            pr = origin.create_pull(
                title=f"RESULTS upload {file_name}",
                body=f"Loading result file for benchmark {benchmark_name}.",
                base=origin.default_branch, head=head
            )
            print(f"Created PR on benchopt results repo: {pr.html_url}")

    print(f"Uploaded file {file_to_upload.name} in benchopt/results")
