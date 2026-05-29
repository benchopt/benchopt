"""Cross-backend install tests.

Exercise ``benchopt install`` against both the ``conda`` and ``uv``
backends. The existing :mod:`test_cmd_install` suite keeps testing
conda-specific paths (env yaml, get_env_info, channel syntax); this
module focuses on behavior shared by every backend.

The uv-flavored tests are skipped when ``uv`` is not available; the
``backend_test_env`` fixture transparently handles env creation /
reuse for both backends.
"""
import shutil

import click
import pytest

from benchopt.cli.main import install
from benchopt.tests.utils import CaptureCmdOutput
from benchopt.utils.temp_benchmark import temp_benchmark


requires_uv = pytest.mark.skipif(
    shutil.which("uv") is None,
    reason="uv is not installed on PATH",
)
requires_conda = pytest.mark.skipif(
    shutil.which("conda") is None,
    reason="conda is not installed on PATH",
)

# Standard parametrize value for cross-backend tests.
backends = pytest.mark.parametrize(
    "backend_test_env",
    [
        pytest.param("conda", marks=requires_conda),
        pytest.param("uv", marks=requires_uv),
    ],
    indirect=True,
)


class TestInstallCmdAcrossBackends:

    @backends
    def test_install_existing_env(self, backend_test_env):
        """The default install path (deps already met) succeeds under each
        backend and prints the ``already available`` line for the standard
        Objective / Dataset / Solver triple."""
        backend, env_name = backend_test_env
        with temp_benchmark() as bench, CaptureCmdOutput() as out:
            install(
                f"{bench.benchmark_dir} -d test-dataset -s test-solver "
                f"--backend {backend} --env-name {env_name}".split(),
                'benchopt', standalone_mode=False,
            )
        out.check_output(f"Installing '{bench.name}' requirements")
        out.check_output(rf"already available in '{env_name}'", repetition=3)

    @backends
    def test_install_specific_backend_via_flag(self, backend_test_env):
        """Passing ``--backend X`` activates the corresponding backend."""
        backend, env_name = backend_test_env
        with temp_benchmark() as bench, CaptureCmdOutput() as out:
            install(
                f"{bench.benchmark_dir} -d test-dataset "
                f"--backend {backend} --env-name {env_name}".split(),
                'benchopt', standalone_mode=False,
            )
        # The header is the same; what we really check is that the call
        # ran end-to-end without erroring under the chosen backend.
        out.check_output(f"Installing '{bench.name}' requirements")


# ---------------------------------------------------------------------------
# Skip-with-warn: uv-only behavior
# ---------------------------------------------------------------------------

@requires_uv
def test_uv_skips_class_with_channel_requirement(test_uv_env_path):
    """A solver whose requirements include a conda channel entry cannot
    be installed under uv. The whole install must keep working, with the
    incompatible class skipped and a warning surfaced.

    We use ``-f`` (force) so that ``collect`` re-evaluates the class
    even though it would import cleanly — the channel requirement
    must still be classified as unsupported.
    """
    chan_solver = """
    from benchopt.utils.temp_benchmark import TempSolver

    class Solver(TempSolver):
        name = "chan-solver"
        requirements = ['pytorch::pytorch']
    """
    with temp_benchmark(solvers=chan_solver) as bench, \
            CaptureCmdOutput() as out:
        install(
            f"{bench.benchmark_dir} -s chan-solver -f "
            f"--backend uv --env-name {test_uv_env_path}".split(),
            'benchopt', standalone_mode=False,
        )
    out.check_output("backend 'uv' cannot install")
    out.check_output("pytorch::pytorch")


# ---------------------------------------------------------------------------
# Requirements backend: end-to-end CLI exercises
# ---------------------------------------------------------------------------

def test_requirements_backend_writes_pip_lines(tmp_path):
    """End-to-end: ``benchopt install --backend requirements`` writes the
    pip-installable requirements of every solver / dataset to the
    configured output file."""
    solver = """
    from benchopt.utils.temp_benchmark import TempSolver

    class Solver(TempSolver):
        name = "pip-solver"
        requirements = ['pip::scikit-learn']
    """
    out = tmp_path / "out.txt"
    with temp_benchmark(solvers=solver) as bench, CaptureCmdOutput() as out_:
        install(
            f"{bench.benchmark_dir} -s pip-solver -f "
            f"--backend requirements --output {out}".split(),
            'benchopt', standalone_mode=False,
        )
    content = out.read_text()
    assert "scikit-learn" in content
    # The pip:: prefix must be stripped in the output.
    assert "pip::" not in content
    out_.check_output(f"Installing '{bench.name}' requirements")
    # The end-of-run message mirrors `benchopt run` / `benchopt plot`.
    out_.check_output(f"Saving requirements in: {out}")


def test_requirements_backend_records_channel_deps_as_manual(tmp_path):
    """Channel-prefixed entries land in the manual-steps section,
    annotated with the class that declared them. The post-install
    verification block must not fire (no env to verify against)."""
    solver = """
    from benchopt.utils.temp_benchmark import TempSolver

    class Solver(TempSolver):
        name = "chan-solver"
        requirements = ['pytorch::pytorch']
    """
    out = tmp_path / "out.txt"
    with temp_benchmark(solvers=solver) as bench:
        with CaptureCmdOutput() as captured:
            install(
                f"{bench.benchmark_dir} -s chan-solver -f "
                f"--backend requirements --output {out}".split(),
                'benchopt', standalone_mode=False,
            )
    content = out.read_text()
    assert "Manual steps" in content
    assert "pytorch" in content
    # The manual entry is attributed to its origin class.
    assert "from chan-solver" in content
    # No post-install verification fires for the export-only backend.
    captured.check_output("Checking installed packages", repetition=0)


def test_requirements_backend_rejects_env_name():
    """``--env-name`` is meaningless under the requirements backend and
    must be rejected at the CLI layer."""
    with temp_benchmark() as bench:
        with pytest.raises(click.BadParameter,
                           match="does not create environments"):
            install(
                f"{bench.benchmark_dir} --backend requirements "
                "--env-name some_env".split(),
                'benchopt', standalone_mode=False,
            )


@requires_uv
def test_uv_installs_pip_solver_alongside_skip(test_uv_env_path):
    """Mixed batch: a uv-installable solver is processed, a conda-only
    one is skipped with a warning. The install does not abort."""
    solvers = (
        """
        from benchopt.utils.temp_benchmark import TempSolver

        class Solver(TempSolver):
            name = "chan-solver"
            requirements = ['pytorch::pytorch']
        """,
        """
        from benchopt.utils.temp_benchmark import TempSolver

        class Solver(TempSolver):
            name = "pip-solver"
            requirements = ['pip::six']
        """,
    )
    with temp_benchmark(solvers=list(solvers)) as bench, \
            CaptureCmdOutput() as out:
        install(
            f"{bench.benchmark_dir} -s chan-solver -s pip-solver -f "
            f"--backend uv --env-name {test_uv_env_path}".split(),
            'benchopt', standalone_mode=False,
        )
    out.check_output("backend 'uv' cannot install")
