import pytest

from benchopt.utils.conda_env_cmd import get_env_file_from_requirements
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.cli.main import run


# TODO: remove this test in benchopt 1.7
def test_deprecated_channel_spec():

    with pytest.warns(DeprecationWarning):
        env = get_env_file_from_requirements(["chan:pkg"])
    assert env == "channels:\n  - chan\ndependencies:\n  - pkg"

    with pytest.warns(DeprecationWarning):
        env = get_env_file_from_requirements(["pip:pkg"])
    assert env == "dependencies:\n  - pip\n  - pip:\n    - pkg"

    with pytest.warns(DeprecationWarning):
        env = get_env_file_from_requirements(["pip:git+https://test.org"])
    assert env == (
        "dependencies:\n  - pip\n  - pip:\n    - git+https://test.org"
    )

    with pytest.warns(DeprecationWarning):
        env = get_env_file_from_requirements(["pkg1", "chan:pkg2", "pip:pkg3"])
    assert env == (
        "channels:\n  - chan\n"
        "dependencies:\n  - pkg1\n  - pkg2\n  - pip\n  - pip:\n    - pkg3"
    )


# TODO: remove this test in benchopt 1.8
def test_deprecated_safe_import_context(no_raise_install):
    solver = """from benchopt import BaseSolver
        from benchopt import safe_import_context

        with safe_import_context() as import_ctx:
            import fake_module

        class Solver(BaseSolver):
            name = 'test-solver'
            def set_objective(self, X, y, lmbd): pass
            def run(self, n_iter): pass
            def get_result(self): return {'beta': 1}
    """

    with temp_benchmark(solvers=solver) as benchmark:
        with pytest.warns(DeprecationWarning, match="safe_import_context"):
            with pytest.raises(SystemExit, match='1'):
                run(
                    f"{benchmark.benchmark_dir} -s test-solver -d test-dataset"
                    " -n 1 -r 1 --no-plot".split(), standalone_mode=False
                )
