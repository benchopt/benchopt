import pytest
import tempfile

from benchopt.cli.main import run
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.dynamic_modules import _load_class_from_module

from benchopt.tests import SELECT_ONE_PGD
from benchopt.tests import SELECT_ONE_SIMULATED
from benchopt.tests import SELECT_ONE_OBJECTIVE
from benchopt.tests import DUMMY_BENCHMARK
from benchopt.tests import DUMMY_BENCHMARK_PATH
from benchopt.tests.utils import patch_import
from benchopt.tests.utils import patch_benchmark
from benchopt.tests.utils import CaptureRunOutput


def test_installcmd_benchmark():
    # Check that an error is raised if the solver's install_cmd is not valid
    
    solver1 = f"""from benchopt import BaseSolver
    import numpy as np
    
    class Solver(BaseSolver):
        name = 'solver2'
        install_cmd = 'pip'
        requirements = ['numpy']
        
        def set_objective(self, X, y):
            pass
            
        def run(self, X, y):
            pass
            
        def get_result(self):
            pass
    """
    
    with temp_benchmark(solvers=[solver1]) as benchmark:
        with patch_benchmark(benchmark):
            with CaptureRunOutput() as capture:
                with pytest.raises(ValueError):
                    run(['install', 'benchmark', DUMMY_BENCHMARK_PATH])