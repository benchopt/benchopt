import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from benchopt.cli.main import run
from benchopt.cli.process_results import publish
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.tests.utils import CaptureCmdOutput


GH_MODULE = "benchopt.results.github"
HF_MODULE = "benchopt.results.hugging_face"
REPO_ID = "my-org/benchopt-results"


class TestCmdPublish:
    """Tests for `benchopt publish --hub huggingface`."""

    def _make_result_file(self, bench):
        """Run the temp benchmark once and return the result file path."""
        with CaptureCmdOutput(delete_result_files=False) as out:
            run(
                f"{bench.benchmark_dir} -d test-dataset --no-plot -n 1"
                .split(), "benchopt", standalone_mode=False,
            )
        return Path(out.result_files[0])

    @pytest.mark.parametrize("hub", ["github", "huggingface"])
    def test_no_file(self, hub):
        """File not found error is raised if the result file doesn't exist."""
        with temp_benchmark() as bench, pytest.raises(
                RuntimeError, match="Could not find any Parquet nor CSV result"
        ):
            publish(
                [str(bench.benchmark_dir), "--hub", hub],
                standalone_mode=False,
            )

    @pytest.mark.parametrize("hub", ["github", "huggingface"])
    def test_invalid_file(self, hub):
        """File not found error is raised if the result file doesn't exist."""
        with temp_benchmark() as bench, pytest.raises(
                FileNotFoundError, match="Could not find result file"
        ):
            self._make_result_file(bench)
            publish(
                [str(bench.benchmark_dir), "--hub", hub, "-f", "bad.csv"],
                standalone_mode=False,
            )

    @pytest.mark.parametrize("hub", ["github", "huggingface"])
    def test_missing_hub_package(self, hub):
        """ImportError with helpful message when the hub package is missing."""
        if hub == "github":
            pkg, hub_module = "github", GH_MODULE
        else:
            pkg, hub_module = "huggingface_hub", HF_MODULE
        err_match = f"{pkg} package is required"
        with temp_benchmark() as bench:
            self._make_result_file(bench)
            # Remove the cached hub module so Python re-executes its top-level
            # import, then block the underlying package so that import fails.
            saved_hub = sys.modules.pop(hub_module, None)
            try:
                with patch.dict('sys.modules', {pkg: None}):
                    with pytest.raises(ImportError, match=err_match):
                        publish(
                            [str(bench.benchmark_dir), "--hub", hub,
                             "-t", "token"],
                            standalone_mode=False,
                        )
            finally:
                if saved_hub is not None:
                    sys.modules[hub_module] = saved_hub


class TestCmdPublishHuggingFace(TestCmdPublish):
    """Tests for `benchopt publish --hub huggingface`."""

    def setup(self):
        pytest.importorskip(
            "huggingface_hub",
            reason="huggingface_hub is required for testing publish on HF."
        )

    @pytest.mark.parametrize(
        "token", [None, "invalid-token"], ids=["no_token", "invalid_token"]
    )
    @patch(f"{HF_MODULE}.HfApi")
    def test_publish_auth_error(self, mock_hf_api_cls, token):
        """An auth error (missing or invalid token) propagates uncaught."""

        if token is None:
            from huggingface_hub.errors import LocalTokenNotFoundError as error
            err_msg = "Could not find the token"
            token_opt = []
        else:
            from requests.exceptions import HTTPError as error
            err_msg = "Invalid token invalid-token"
            token_opt = ["-t", token]

        with temp_benchmark() as bench:
            self._make_result_file(bench)

            mock_api = MagicMock()
            mock_hf_api_cls.return_value = mock_api
            mock_api.whoami.side_effect = error()

            with pytest.raises(RuntimeError, match=err_msg):
                publish(
                    [str(bench.benchmark_dir), "--hub", "huggingface",
                        "-R", REPO_ID, *token_opt],
                    standalone_mode=False,
                )

        mock_api.whoami.assert_called_once()
        mock_api.create_repo.assert_not_called()
        mock_api.upload_file.assert_not_called()

    @patch(f"{HF_MODULE}.hf_hub_download")
    @patch(f"{HF_MODULE}.HfApi")
    def test_publish_repo_exists_file_not_found(
        self, mock_hf_api_cls, mock_hf_download
    ):
        """Repo exists but no matching file in it: file is uploaded fresh."""
        from huggingface_hub.utils import EntryNotFoundError

        with temp_benchmark() as bench:
            self._make_result_file(bench)

            mock_api = MagicMock()
            mock_hf_api_cls.return_value = mock_api
            mock_api.repo_info.return_value = MagicMock()
            mock_hf_download.side_effect = EntryNotFoundError("File not found")

            with CaptureCmdOutput() as out:
                publish(
                    f"{bench.benchmark_dir} --hub huggingface -R {REPO_ID}"
                    .split(),
                    standalone_mode=False,
                )

        mock_hf_api_cls.assert_called_once_with(token=None)
        mock_api.repo_info.assert_called_once()
        mock_api.create_repo.assert_not_called()
        mock_hf_download.assert_called_once()
        mock_api.upload_file.assert_called_once()
        out.check_output("uploading fresh")

    @patch(f"{HF_MODULE}.hf_hub_download")
    @patch(f"{HF_MODULE}.HfApi")
    def test_publish_repo_exists_file_exists(
        self, mock_hf_api_cls, mock_hf_download
    ):
        """Repo and file exist: results are merged then re-uploaded."""
        with temp_benchmark() as bench:
            result_file = self._make_result_file(bench)

            mock_api = MagicMock()
            mock_hf_api_cls.return_value = mock_api
            # repo_info does not raise -> repo already exists
            mock_api.repo_info.return_value = MagicMock()
            # hf_hub_download returns the same local file to simulate an
            # existing remote CSV (merge_results will read it as the prior run)
            mock_hf_download.return_value = str(result_file)

            with CaptureCmdOutput() as out:
                publish(
                    f"{bench.benchmark_dir} --hub huggingface -R {REPO_ID}"
                    .split(),
                    standalone_mode=False,
                )

        mock_hf_api_cls.assert_called_once_with(token=None)
        mock_api.repo_info.assert_called_once()
        mock_api.create_repo.assert_not_called()
        mock_hf_download.assert_called_once()
        mock_api.upload_file.assert_called_once()
        out.check_output("merging")

    @patch(f"{HF_MODULE}.hf_hub_download")
    @patch(f"{HF_MODULE}.HfApi")
    def test_publish_repo_not_found(self, mock_hf_api_cls, mock_hf_download):
        """Repo doesn't exist: it is created before uploading."""
        from huggingface_hub.utils import (
            EntryNotFoundError, RepositoryNotFoundError
        )

        with temp_benchmark() as bench:
            self._make_result_file(bench)

            mock_api = MagicMock()
            mock_hf_api_cls.return_value = mock_api
            mock_api.repo_info.side_effect = RepositoryNotFoundError(
                "Repository Not Found"
            )
            # New repo -> no existing file
            mock_hf_download.side_effect = EntryNotFoundError("File not found")

            with CaptureCmdOutput() as out:
                publish(
                    f"{bench.benchmark_dir} --hub huggingface -R {REPO_ID}"
                    .split(),
                    standalone_mode=False,
                )

        mock_api.repo_info.assert_called_once()
        mock_api.create_repo.assert_called_once_with(
            repo_id=REPO_ID, repo_type="dataset", exist_ok=True
        )
        mock_api.upload_file.assert_called_once()
        out.check_output("not found, creating")


class TestCmdPublishGitHub(TestCmdPublish):
    """Tests for `benchopt publish --hub github` (default hub)."""

    def setup(self):
        pytest.importorskip(
            "github",
            reason="PyGithub is required for testing publish on GitHub."
        )

    def _setup_github_mock(self, mock_Github, username="testuser"):
        """Set up Github mock hierarchy and return
            (mock_g, mock_origin, mock_fork).
        """
        mock_g = MagicMock()
        mock_Github.return_value = mock_g
        mock_g.get_user.return_value.login = username

        mock_origin = MagicMock()
        mock_g.get_repo.return_value = mock_origin
        mock_origin.default_branch = "main"

        mock_fork = MagicMock()
        mock_origin.create_fork.return_value = mock_fork
        # Branch exists by default
        mock_fork.get_branch.return_value = MagicMock()

        return mock_g, mock_origin, mock_fork

    @patch("benchopt.cli.process_results.get_setting", return_value=None)
    @patch(f"{GH_MODULE}.Github")
    def test_publish_auth_error_no_token(self, mock_Github, _):
        """No token raises RuntimeError."""

        with temp_benchmark() as bench:
            self._make_result_file(bench)

            # Ensure get_setting also returns None so no token is found
            with pytest.raises(RuntimeError, match="Could not find the token"):
                publish(
                    [str(bench.benchmark_dir), "--hub", "github"],
                    standalone_mode=False,
                )
            mock_Github.assert_not_called()

    @patch(f"{GH_MODULE}.Github")
    def test_publish_auth_error_invalid_token(self, mock_Github):
        """Invalid token propagates GithubException."""
        from github import GithubException

        with temp_benchmark() as bench:
            self._make_result_file(bench)
            mock_g = MagicMock()
            mock_Github.return_value = mock_g
            mock_g.get_user.side_effect = GithubException(
                401, {"message": "Bad credentials"}
            )
            with pytest.raises(GithubException):
                publish(
                    [str(bench.benchmark_dir), "--hub", "github",
                        "-t", "invalid-token"],
                    standalone_mode=False,
                )
            mock_Github.assert_called_once_with(
                login_or_token="invalid-token"
            )
            mock_g.get_user.assert_called_once()

    @patch(f"{GH_MODULE}.Github")
    def test_publish_new_file(self, mock_Github):
        """File doesn't exist in branch: it is created and a PR is opened."""
        from github import GithubException

        with temp_benchmark() as bench:
            self._make_result_file(bench)

            _, mock_origin, mock_fork = self._setup_github_mock(mock_Github)
            # Branch doesn't exist -> create it from origin's default branch
            mock_fork.get_branch.side_effect = GithubException(
                404, {"message": "Branch not found"}
            )
            mock_origin.get_branch.return_value.commit.sha = "deadbeef"
            # Result file and meta.json are absent from the fork
            mock_fork.get_contents.side_effect = GithubException(
                404, {"message": "Not Found"}
            )
            # No existing open PR -> a new one is created
            mock_origin.get_pulls.return_value = []
            mock_pr = MagicMock()
            mock_pr.html_url = "https://github.com/benchopt/results/pull/42"
            mock_origin.create_pull.return_value = mock_pr

            with CaptureCmdOutput() as out:
                publish(
                    [str(bench.benchmark_dir), "--hub", "github",
                     "-t", "valid-token"],
                    standalone_mode=False,
                )

        mock_fork.create_git_ref.assert_called_once()
        assert mock_fork.create_file.call_count == 2  # result file + meta.json
        mock_fork.update_file.assert_not_called()
        mock_origin.create_pull.assert_called_once()
        out.check_output("Created PR")
        out.check_output("Uploaded file")

    @patch(f"{GH_MODULE}.Github")
    def test_publish_file_already_uploaded(self, mock_Github):
        """File exists with identical content: publish is a no-op."""
        with temp_benchmark() as bench:
            result_file = self._make_result_file(bench)
            file_content = result_file.read_bytes()

            _, mock_origin, mock_fork = self._setup_github_mock(mock_Github)
            mock_contents = MagicMock()
            mock_contents.decoded_content = file_content
            mock_contents.sha = "abc123"
            # get_contents is called once then early-returns (no meta.json)
            mock_fork.get_contents.return_value = mock_contents

            with CaptureCmdOutput() as out:
                publish(
                    [str(bench.benchmark_dir), "--hub", "github",
                     "-t", "valid-token"],
                    standalone_mode=False,
                )

        mock_fork.create_file.assert_not_called()
        mock_fork.update_file.assert_not_called()
        mock_origin.create_pull.assert_not_called()
        out.check_output("already uploaded")

    @patch(f"{GH_MODULE}.Github")
    def test_publish_file_updated(self, mock_Github):
        """File exists but content differs: update it and create a PR."""
        from github import GithubException

        with temp_benchmark() as bench:
            self._make_result_file(bench)

            _, mock_origin, mock_fork = self._setup_github_mock(mock_Github)
            mock_contents = MagicMock()
            mock_contents.decoded_content = b"outdated content"
            mock_contents.sha = "abc123"
            # First call: result file found with stale content;
            # second call: meta.json absent -> create it
            mock_fork.get_contents.side_effect = [
                mock_contents,
                GithubException(404, {"message": "Not Found"}),
            ]
            mock_origin.get_pulls.return_value = []
            mock_origin.create_pull.return_value = MagicMock(
                html_url="https://github.com/benchopt/results/pull/43"
            )

            with CaptureCmdOutput() as out:
                publish(
                    [str(bench.benchmark_dir), "--hub", "github",
                     "-t", "valid-token"],
                    standalone_mode=False,
                )

        mock_fork.update_file.assert_called_once()  # result file updated
        mock_fork.create_file.assert_called_once()  # meta.json created
        mock_origin.create_pull.assert_called_once()
        out.check_output("Uploaded file")
