from benchopt.utils.safe_import import (mock_all_import,
                                        mock_failed_import,
                                        _unmock_import,
                                        safe_import_context)
from benchopt.utils.temp_benchmark import temp_benchmark
from unittest.mock import Mock
import sys


def test_mock_all_import():
    mock_all_import()

    with safe_import_context():
        import unknown_module
        import this

    assert isinstance(unknown_module, Mock)
    assert isinstance(this, Mock)

    sys.modules.pop('unknown_module')
    sys.modules.pop('this')

    _unmock_import()


def test_mock_failed_import():
    mock_failed_import()

    with safe_import_context():
        import unknown_module
        import this

    assert isinstance(unknown_module, Mock)
    assert not isinstance(this, Mock)

    sys.modules.pop('unknown_module')
    sys.modules.pop('this')

    _unmock_import()


def test_mock_all_import_with_benchmark():
    mock_all_import()

    objective = """from benchopt import BaseObjective, safe_import_context
            with safe_import_context() as import_ctx:
                import unknown_module_objective
                import this

            class Objective(BaseObjective):
                name = "mock"

                def set_data(self, X, y): pass
                def get_objective(self): pass
                def get_one_result(self): pass
                def evaluate_result(self, beta): pass
        """

    solver = """
        from benchopt import BaseSolver, safe_import_context

        with safe_import_context() as import_ctx:
                import unknown_module_solver
                import nis

        class Solver(BaseSolver):
            name = "test-solver"
            sampling_strategy = 'run_once'
            def set_objective(self, X_train, y_train): pass
            def run(self, n_iter): print("OK")
            def get_result(self): return dict(beta=1)
    """

    dataset = """
        from benchopt import BaseDataset, safe_import_context

        with safe_import_context() as import_ctx:
                import unknown_module_dataset
                import chunk

        class Dataset(BaseDataset):
            name = "custom_dataset"
            def get_data(self): pass
    """

    with temp_benchmark(
            objective=objective,
            datasets=[dataset],
            solvers=[solver]) as benchmark:
        benchmark.get_solvers()
        benchmark.get_datasets()
        assert isinstance(sys.modules.get('unknown_module_objective'), Mock)
        assert isinstance(sys.modules.get('unknown_module_solver'), Mock)
        assert isinstance(sys.modules.get('unknown_module_dataset'), Mock)
        assert isinstance(sys.modules.get('this'), Mock)
        assert isinstance(sys.modules.get('nis'), Mock)
        assert isinstance(sys.modules.get('chunk'), Mock)

    sys.modules.pop('unknown_module_objective')
    sys.modules.pop('unknown_module_solver')
    sys.modules.pop('unknown_module_dataset')
    sys.modules.pop('this')
    sys.modules.pop('nis')
    sys.modules.pop('chunk')

    _unmock_import()


def test_mock_failed_import_with_benchmark():
    mock_failed_import()

    objective = """from benchopt import BaseObjective, safe_import_context
                with safe_import_context() as import_ctx:
                    import unknown_module_objective
                    import this

                class Objective(BaseObjective):
                    name = "mock"

                    def set_data(self, X, y): pass
                    def get_objective(self): pass
                    def get_one_result(self): pass
                    def evaluate_result(self, beta): pass
            """

    solver = """
            from benchopt import BaseSolver, safe_import_context

            with safe_import_context() as import_ctx:
                    import unknown_module_solver
                    import nis

            class Solver(BaseSolver):
                name = "test-solver"
                sampling_strategy = 'run_once'
                def set_objective(self, X_train, y_train): pass
                def run(self, n_iter): print("OK")
                def get_result(self): return dict(beta=1)
        """

    dataset = """
            from benchopt import BaseDataset, safe_import_context

            with safe_import_context() as import_ctx:
                    import unknown_module_dataset
                    import chunk

            class Dataset(BaseDataset):
                name = "custom_dataset"
                def get_data(self): pass
        """

    with temp_benchmark(objective=objective,
                        datasets=[dataset],
                        solvers=[solver]) as benchmark:
        benchmark.get_solvers()
        benchmark.get_datasets()
        assert isinstance(sys.modules.get('unknown_module_objective'), Mock)
        assert isinstance(sys.modules.get('unknown_module_solver'), Mock)
        assert isinstance(sys.modules.get('unknown_module_dataset'), Mock)
        assert not isinstance(sys.modules.get('this'), Mock)
        assert not isinstance(sys.modules.get('nis'), Mock)
        assert not isinstance(sys.modules.get('chunk'), Mock)

        sys.modules.pop('unknown_module_objective')
        sys.modules.pop('unknown_module_solver')
        sys.modules.pop('unknown_module_dataset')
        sys.modules.pop('this')
        sys.modules.pop('nis')
        sys.modules.pop('chunk')

    _unmock_import()
