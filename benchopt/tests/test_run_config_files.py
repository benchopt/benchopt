import pytest

from benchopt.cli.main import run
from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils import CaptureCmdOutput

SOLVER = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        sampling_strategy = 'iteration'
        parameters = dict(param1=[None], param2=[None])

        def set_objective(self, X, y, lmbd): pass
        def run(self, n_iter): print(f"RUN({n_iter})")
        def get_result(self): return {'beta': 1}
"""

CONFIG = """
    objective:
        - test-objective
    dataset:
        - test-dataset
    solver:
        - solver1 #PARAMS
    n-repetitions: 1
    max-runs: 0
    plot: false
"""


def test_config_solver_no_params(no_debug_log):
    config = {"run_config.yml": CONFIG}
    solver = SOLVER.replace(
        "parameters = dict(param1=[None], param2=[None])", ""
    )
    with temp_benchmark(solvers=solver, config=config) as bench:
        with CaptureCmdOutput() as out:
            config_file = bench.benchmark_dir / "run_config.yml"
            run([
                str(bench.benchmark_dir),
                *f'--config {config_file}'.split()
            ], standalone_mode=False)
        out.check_output(r"RUN\(0\)", repetition=1)


def test_config_solver_no_params_error(no_debug_log):
    config = {"run_config.yml": CONFIG.replace(" #PARAMS", "[param1=0]")}
    solver = SOLVER.replace(
        "parameters = dict(param1=[None], param2=[None])", ""
    )
    with temp_benchmark(solvers=solver, config=config) as bench:
        error = (
            "Unknown parameter 'param1' for solver solver1.\n"
            "This solver has no parameters."
        )
        config_file = bench.benchmark_dir / "run_config.yml"
        with CaptureCmdOutput():
            with pytest.raises(ValueError, match=error):
                run([
                    str(bench.benchmark_dir),
                    *f'--config {config_file}'.split()
                ], standalone_mode=False)


def test_config_solver_with_params(no_debug_log):
    config = {"run_config.yml": CONFIG}
    with temp_benchmark(solvers=SOLVER, config=config) as bench:
        config_file = bench.benchmark_dir / "run_config.yml"
        with CaptureCmdOutput() as out:
            run([
                str(bench.benchmark_dir),
                *f'--config {config_file}'.split()
            ], standalone_mode=False)
        out.check_output(r"RUN\(0\)", repetition=1)
        out.check_output(r"solver1\[param1=None,param2=None\]", repetition=2)


def test_config_solver_with_params_error(no_debug_log):
    config = {"run_config.yml": CONFIG.replace(" #PARAMS", "[param0=0]")}

    with temp_benchmark(solvers=SOLVER, config=config) as bench:
        config_file = bench.benchmark_dir / "run_config.yml"

        error = (
            "Unknown parameter 'param0' for solver solver1.\n"
            "Possible parameters are:\n- param1\n- param2"
        )

        with CaptureCmdOutput():
            with pytest.raises(ValueError, match=error):
                run([
                    str(bench.benchmark_dir),
                    *f'--config {config_file}'.split()
                ], standalone_mode=False)


def test_config_solver_with_params_list_error(no_debug_log):
    config = {"run_config.yml": CONFIG.replace(" #PARAMS", "[0, 1]")}

    with temp_benchmark(solvers=SOLVER, config=config) as bench:
        config_file = bench.benchmark_dir / "run_config.yml"

        error = "Ambiguous positional parameter for solver1."
        with CaptureCmdOutput():
            with pytest.raises(ValueError, match=error):
                run([
                    str(bench.benchmark_dir),
                    *f'--config {config_file}'.split()
                ], standalone_mode=False)


def test_config_solver_with_params_str_list(no_debug_log):
    config = {"run_config.yml": CONFIG.replace(" #PARAMS", "[param1=[0, 1]]")}

    with temp_benchmark(solvers=SOLVER, config=config) as bench:
        config_file = bench.benchmark_dir / "run_config.yml"
        with CaptureCmdOutput() as out:
            run([
                str(bench.benchmark_dir),
                *f'--config {config_file}'.split()
            ], standalone_mode=False)
        out.check_output(r"RUN\(0\)", repetition=2)
        out.check_output("param1=None", repetition=0)
        out.check_output("param1=0,param2=None", repetition=2)
        out.check_output("param1=1,param2=None", repetition=2)


def test_config_solver_with_params_str_value(no_debug_log):
    config = {
        "run_config.yml": CONFIG.replace(" #PARAMS", "[param1=0, param2=1]")
    }

    with temp_benchmark(solvers=SOLVER, config=config) as bench:
        config_file = bench.benchmark_dir / "run_config.yml"
        with CaptureCmdOutput() as out:
            run([
                str(bench.benchmark_dir),
                *f'--config {config_file}'.split()
            ], standalone_mode=False)
        out.check_output(r"RUN\(0\)", repetition=1)
        out.check_output("param1=None", repetition=0)
        out.check_output("param2=None", repetition=0)
        out.check_output("param1=0,param2=1", repetition=2)


def test_config_solver_with_params_yaml_list(no_debug_log):
    config = {"run_config.yml": CONFIG.replace(
        " #PARAMS", ":\n            param1: [0, 1]"
    )}

    with temp_benchmark(solvers=SOLVER, config=config) as bench:
        config_file = bench.benchmark_dir / "run_config.yml"
        with CaptureCmdOutput() as out:
            run([
                str(bench.benchmark_dir),
                *f'--config {config_file}'.split()
            ], standalone_mode=False)
        out.check_output(r"RUN\(0\)", repetition=2)
        out.check_output("param1=None", repetition=0)
        out.check_output("param1=0,param2=None", repetition=2)
        out.check_output("param1=1,param2=None", repetition=2)


def test_config_solver_with_params_yaml_items(no_debug_log):
    config = {"run_config.yml": CONFIG.replace(" #PARAMS", """:
              param1:
                - 0
                - 1
    """)}
    with temp_benchmark(solvers=SOLVER, config=config) as bench:
        config_file = bench.benchmark_dir / "run_config.yml"
        with CaptureCmdOutput() as out:
            run([
                str(bench.benchmark_dir),
                *f'--config {config_file}'.split()
            ], standalone_mode=False)
        out.check_output(r"RUN\(0\)", repetition=2)
        out.check_output("param1=None", repetition=0)
        out.check_output("param1=0", repetition=2)
        out.check_output("param1=1", repetition=2)


def test_config_solver_with_params_yaml_value(no_debug_log):
    config = {"run_config.yml": CONFIG.replace(" #PARAMS", """:
              param1: 0
              param2: 1
    """)}
    with temp_benchmark(solvers=SOLVER, config=config) as bench:
        config_file = bench.benchmark_dir / "run_config.yml"
        with CaptureCmdOutput() as out:
            run([
                str(bench.benchmark_dir),
                *f'--config {config_file}'.split()
            ], standalone_mode=False)
        out.check_output(r"RUN\(0\)", repetition=1)
        out.check_output("param1=None", repetition=0)
        out.check_output("param2=None", repetition=0)
        out.check_output("param1=0,param2=1", repetition=2)


def test_config_solver_with_params_complex_param(no_debug_log):
    config = {"run_config.yml": CONFIG.replace(" #PARAMS", """:
              param1:
                - test: 0
                  test2: 1
    """)}
    with temp_benchmark(solvers=SOLVER, config=config) as bench:
        config_file = bench.benchmark_dir / "run_config.yml"
        with CaptureCmdOutput() as out:
            run([
                str(bench.benchmark_dir),
                *f'--config {config_file}'.split()
            ], standalone_mode=False)
        out.check_output("param1=None", repetition=0)
        out.check_output(
            "param1={'test': 0, 'test2': 1},param2=None",
            repetition=2
        )


def test_config_solver_with_one_param_list(no_debug_log):
    config = {"run_config.yml": CONFIG.replace(" #PARAMS", "[0, 1]")}
    solver = SOLVER.replace("param2=[None]", "")

    with temp_benchmark(solvers=solver, config=config) as bench:
        config_file = bench.benchmark_dir / "run_config.yml"

        with CaptureCmdOutput() as out:
            run([
                str(bench.benchmark_dir),
                *f'--config {config_file}'.split()
            ], standalone_mode=False)
        out.check_output(r"RUN\(0\)", repetition=2)
        out.check_output("param1=None", repetition=0)
        out.check_output("param1=0", repetition=2)
        out.check_output("param1=1", repetition=2)


def test_config_solver_with_one_param_yaml_list(no_debug_log):
    config = {"run_config.yml": CONFIG.replace(
        " #PARAMS", ":\n          - 0\n          - 1"
    )}
    solver = SOLVER.replace("param2=[None]", "")

    with temp_benchmark(solvers=solver, config=config) as bench:
        config_file = bench.benchmark_dir / "run_config.yml"

        with CaptureCmdOutput() as out:
            run([
                str(bench.benchmark_dir),
                *f'--config {config_file}'.split()
            ], standalone_mode=False)
        out.check_output(r"RUN\(0\)", repetition=2)
        out.check_output("param1=None", repetition=0)
        out.check_output("param1=0", repetition=2)
        out.check_output("param1=1", repetition=2)


def test_config_solver_double_param_yaml_list(no_debug_log):
    config = {"run_config.yml": CONFIG.replace(
        " #PARAMS", ":\n            param1, param2: [[0, 1]]"
    )}

    with temp_benchmark(solvers=SOLVER, config=config) as bench:
        config_file = bench.benchmark_dir / "run_config.yml"

        with CaptureCmdOutput() as out:
            run([
                str(bench.benchmark_dir),
                *f'--config {config_file}'.split()
            ], standalone_mode=False)
        out.check_output(r"RUN\(0\)", repetition=1)
        out.check_output("param1=None", repetition=0)
        out.check_output("param2=None", repetition=0)
        out.check_output("param1=0,param2=1", repetition=2)


def test_config_solver_double_param_solver_yaml(no_debug_log):
    config = {"run_config.yml": CONFIG.replace(" #PARAMS", "[param1=0]")}

    with temp_benchmark(solvers=SOLVER, config=config) as bench:
        config_file = bench.benchmark_dir / "run_config.yml"

        with CaptureCmdOutput() as out:
            run([
                str(bench.benchmark_dir),
                *f'--config {config_file}'.split()
            ], standalone_mode=False)
        out.check_output(r"RUN\(0\)", repetition=1)
        out.check_output("param1=None", repetition=0)
        out.check_output("param1=0,param2=None", repetition=2)
