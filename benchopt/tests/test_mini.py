import pytest

from benchopt.utils.temp_benchmark import temp_mini_benchmark
from benchopt.benchmark import Benchmark
from benchopt.cli.main import run

from benchopt.tests.utils import CaptureRunOutput


def test_mini_bench_bases():
    with temp_mini_benchmark() as benchmark:
        assert isinstance(benchmark, Benchmark)
        assert benchmark.get_benchmark_objective().__name__ == '_Objective'
        solvers = benchmark.get_solvers()
        assert len(solvers) == 1
        assert solvers[0].__name__ == '_Solver'
        datasets = benchmark.get_datasets()
        assert len(datasets) == 1
        assert datasets[0].__name__ == '_Dataset'


def test_mini_bench_multiple_bases():
    mini_bench = """from benchopt.mini import solver, dataset, objective
            import jax
            
            @dataset(
                size=100,
                random_state=0
            )
            def simulated(size, random_state):
                key = jax.random.PRNGKey(random_state)
                key, subkey = jax.random.split(key)
                X = jax.random.normal(key, (size,))
                return dict(X=X)
            
            
            @dataset(
                size=100,
                random_state=0
            )
            def simulated2(size, random_state):
                key = jax.random.PRNGKey(random_state)
                key, subkey = jax.random.split(key)
                X = jax.random.normal(key, (size,))
                return dict(X=X)
            
            
            @solver(
                name="Solver 1",
                lr=[1e-2, 1e-3]
            )
            def solver1(n_iter, X, lr):
                beta = X
                for i in range(n_iter):
                    beta -= lr * beta
            
                return dict(beta=beta)

            
            @solver(
                name="Solver 2",
                lr=[1e-2, 1e-3]
            )
            def solver2(n_iter, X, lr):
                beta = X
                for i in range(n_iter):
                    beta -= lr * beta
            
                return dict(beta=beta)
            
            
            @objective(name="Benchmark HVP")
            def evaluate(beta):
                return dict(value=(0.5 * beta.dot(beta)).item())
    """

    with temp_mini_benchmark(mini_bench=mini_bench) as benchmark:
        assert isinstance(benchmark, Benchmark)
        assert benchmark.get_benchmark_objective().__name__ == '_Objective'
        solvers = benchmark.get_solvers()
        assert len(solvers) == 2
        assert solvers[0].__name__ == '_Solver'
        assert solvers[1].__name__ == '_Solver'
        datasets = benchmark.get_datasets()
        assert len(datasets) == 2
        assert datasets[0].__name__ == '_Dataset'
        assert datasets[1].__name__ == '_Dataset'


@pytest.mark.parametrize('n_jobs', [1, 2])
def test_run_mini_bench(n_jobs):
    with temp_mini_benchmark() as benchmark:
        with CaptureRunOutput() as out:
            run(['--mini', str(benchmark.mini_file),
                 '-j', n_jobs, '--no-plot'],
                'benchopt', standalone_mode=False)

        out.check_output('simulated', repetition=1)
        out.check_output('Benchmark HVP', repetition=1)
        out.check_output(r'Solver 1\[lr=0.01\]', repetition=59)
        out.check_output(r'Solver 1\[lr=0.001\]', repetition=71)

        # Make sure the results were saved in a result file
        assert len(out.result_files) == 1, out.output


def test_multiple_objective():
    mini_bench = """from benchopt.mini import solver, dataset, objective
        import jax

        @dataset(
            size=100,
            random_state=0
        )
        def simulated(size, random_state):
            key = jax.random.PRNGKey(random_state)
            key, subkey = jax.random.split(key)
            X = jax.random.normal(key, (size,))
            return dict(X=X)


        @solver(
            name="Solver 1",
            lr=[1e-2, 1e-3]
        )
        def solver1(n_iter, X, lr):
            beta = X
            for i in range(n_iter):
                beta -= lr * beta

            return dict(beta=beta)


        @objective(name="Benchmark HVP")
        def evaluate(beta):
            return dict(value=(0.5 * beta.dot(beta)).item())
            

        @objective(name="Benchmark HVP")
        def evaluate2(beta):
            return dict(value=(0.5 * beta.dot(beta)).item())
    """
    with pytest.raises(AssertionError, match="Can only call objective decorator once."):
        with temp_mini_benchmark(mini_bench=mini_bench) as benchmark:
            pass


def test_empty_objective():
    mini_bench = """from benchopt.mini import solver, dataset, objective
        import jax

        @dataset(
            size=100,
            random_state=0
        )
        def simulated(size, random_state):
            key = jax.random.PRNGKey(random_state)
            key, subkey = jax.random.split(key)
            X = jax.random.normal(key, (size,))
            return dict(X=X)


        @solver(
            name="Solver 1",
            lr=[1e-2, 1e-3]
        )
        def solver1(n_iter, X, lr):
            beta = X
            for i in range(n_iter):
                beta -= lr * beta

            return dict(beta=beta)
    """

    with pytest.raises(AssertionError, match="Need to set one objective."):
        with temp_mini_benchmark(mini_bench=mini_bench) as benchmark:
            pass


def test_empty_solvers():
    mini_bench = """from benchopt.mini import solver, dataset, objective
            import jax

            @dataset(
                size=100,
                random_state=0
            )
            def simulated(size, random_state):
                key = jax.random.PRNGKey(random_state)
                key, subkey = jax.random.split(key)
                X = jax.random.normal(key, (size,))
                return dict(X=X)


            @objective(name="Benchmark HVP")
            def evaluate(beta):
                return dict(value=(0.5 * beta.dot(beta)).item())
        """
    with pytest.raises(AssertionError, match="Need to set at least one solver."):
        with temp_mini_benchmark(mini_bench=mini_bench) as benchmark:
            pass


def test_empty_datasets():
    mini_bench = """from benchopt.mini import solver, dataset, objective
        import jax


        @solver(
            name="Solver 1",
            lr=[1e-2, 1e-3]
        )
        def solver1(n_iter, X, lr):
            beta = X
            for i in range(n_iter):
                beta -= lr * beta

            return dict(beta=beta)


        @objective(name="Benchmark HVP")
        def evaluate(beta):
            return dict(value=(0.5 * beta.dot(beta)).item())
    """

    with pytest.raises(AssertionError, match="Need to set at least one dataset."):
        with temp_mini_benchmark(mini_bench=mini_bench) as benchmark:
            pass
