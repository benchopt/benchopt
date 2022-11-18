import pytest

from benchopt.cli.main import run

from benchopt.tests import CaptureRunOutput
from benchopt.tests import SELECT_ONE_PGD
from benchopt.tests import SELECT_ONE_SIMULATED
from benchopt.tests import SELECT_ONE_OBJECTIVE
from benchopt.tests import DUMMY_BENCHMARK
from benchopt.tests import DUMMY_BENCHMARK_PATH
from benchopt.tests import FUTURE_BENCHMARK_PATH

from benchopt.utils.dynamic_modules import _load_class_from_module


def test_template_dataset():
    # Make sure that importing template_dataset raises an error.
    with pytest.raises(ImportError):
        template_dataset = (
            DUMMY_BENCHMARK_PATH / 'datasets' / 'template_dataset.py'
        )
        _load_class_from_module(
            template_dataset, 'Dataset', DUMMY_BENCHMARK_PATH
        )

    # Make sure that this error is not raised when listing all datasets from
    # the benchmark.
    DUMMY_BENCHMARK.get_datasets()


def test_template_solver():
    # Make sure that importing template_dataset raises an error.
    with pytest.raises(ImportError):
        template_dataset = (
            DUMMY_BENCHMARK_PATH / 'solvers' / 'template_solver.py'
        )
        _load_class_from_module(
            template_dataset, 'Solver', DUMMY_BENCHMARK_PATH
        )

    # Make sure that this error is not raised when listing all solvers from
    # the benchmark.
    DUMMY_BENCHMARK.get_solvers()


def test_benchmark_submodule():
    with pytest.raises(ValueError, match="raises an error"):
        run([
            str(DUMMY_BENCHMARK_PATH), '-s', 'Test-Solver[raise_error=True]',
            '-d', SELECT_ONE_SIMULATED
        ], 'benchopt', standalone_mode=False)


def test_benchopt_min_version():
    with pytest.raises(RuntimeError, match="pip install -U"):
        run([str(FUTURE_BENCHMARK_PATH)], 'benchopt', standalone_mode=False)

    with CaptureRunOutput() as out:
        # check than benchmark with low requirement runs
        run([
            str(DUMMY_BENCHMARK_PATH), '-l', '-d', SELECT_ONE_SIMULATED,
            '-f', SELECT_ONE_PGD, '-n', '1', '-r', '1', '-o',
            SELECT_ONE_OBJECTIVE, '--no-plot'
        ], 'benchopt', standalone_mode=False)

    out.check_output('Simulated', repetition=1)


def test_error_reporting():

    import os
    os.environ['BENCHOPT_RAISE_INSTALL_ERROR'] = '0'

    with CaptureRunOutput() as out:
        with pytest.raises(SystemExit):
            run([
                str(DUMMY_BENCHMARK_PATH), '-s', "importerror",
                '-d', SELECT_ONE_SIMULATED
            ], 'benchopt', standalone_mode=False)

    assert "ImportError: This should not be imported" in out.output

    with CaptureRunOutput() as out:
        with pytest.raises(SystemExit):
            run([
                str(DUMMY_BENCHMARK_PATH), '-s', "valueerror",
                '-d', SELECT_ONE_SIMULATED
            ], 'benchopt', standalone_mode=False)

    assert "ValueError: This should not be run" in out.output
