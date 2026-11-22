import shutil
import pytest
import inspect
import numpy as np
import warnings

from benchopt.stopping_criterion import StoppingCriterion
from benchopt.stopping_criterion import SAMPLING_STRATEGIES
from benchopt.utils.dynamic_modules import _get_module_from_file
from benchopt.utils.parametrized_name_mixin import get_configs
from benchopt.utils.run_context import RunContext
from benchopt.callback import _Callback


def test_dataset_class(benchmark, dataset_class):
    """Check that all dataset_class respects the public API"""

    # Check that the dataset_class exposes a name
    assert hasattr(dataset_class, 'name'), "All dataset should expose a name"
    assert isinstance(dataset_class.name, str), (
        "The dataset's name should be a string")
    assert '/' not in dataset_class.name, (
        f"The dataset's name should not contain '/' (got "
        f"'{dataset_class.name}'). A '/' makes the name ambiguous with a "
        "`-d path/to/dataset.py` file selector."
    )

    # Ensure that the dataset exposes a `get_data` function
    # that is callable
    assert hasattr(dataset_class, 'get_data'), (
        "All dataset should implement get_data"
    )
    assert callable(dataset_class.get_data), (
        "dataset.get_data should be a callable"
    )


@pytest.mark.requires_install
def test_dataset_install(test_env_name, benchmark, dataset_class):

    # Make sure that the current benchmark is correctly set
    from benchopt.benchmark import Benchmark
    benchmark = Benchmark(benchmark.benchmark_dir)

    # assert that install works when forced to reinstalls
    dataset_class.install(env_name=test_env_name)
    dataset_class.is_installed(
        env_name=test_env_name, raise_on_not_installed=True
    )


def test_dataset_get_data(benchmark, dataset_class):
    """Check that all installed dataset_class.get_data return the right result
    """

    # skip the test if the dataset is not installed
    if not dataset_class.is_installed():
        pytest.skip("Dataset is not installed")

    # instanciate dataset taking into account the test_config
    config = get_configs(dataset_class)[0]
    dataset = dataset_class.get_instance(**config['dataset'])

    # ensure classes calling `get_seed` work properly. Use placeholder
    # objective/solver names to mimic known dimension at runtime.
    with RunContext(
        objective="dummy", dataset=dataset, solver="dummy",
        repetition=0, base_seed=0
    ):
        data = dataset.get_data()
    assert isinstance(data, (tuple, dict)), (
        "Output of get_data should be a 2-tuple or a dict."
    )

    assert isinstance(data, dict), (
        f"The returned data from get_data should be a dict. Got {data}."
    )


def test_benchmark_objective(benchmark, test_dataset_name):
    # check that the result of the objective function is compatible with
    # benchopt, does not contain `objective_name` and is not empty.

    # instanciate dataset and objective, taking into account the test_config
    objective_class = benchmark.get_benchmark_objective()
    dataset_class = benchmark.get_test_dataset(name=test_dataset_name)
    config = get_configs(dataset_class, objective_class)[0]
    dataset = dataset_class.get_instance(**config['dataset'])
    objective = objective_class.get_instance(**config['objective'])

    # ensure classes calling `get_seed` work properly. Use a placeholder
    # solver name so all methods can use any seed dimension.
    with RunContext(
        objective=objective, dataset=dataset, solver="dummy",
        repetition=0, base_seed=0
    ):
        # get one value for the objective, with the test_dataset
        objective._load_data()
        result = objective._get_one_result()
        if result is None:
            pytest.skip(
                "Objective needs to implement get_one_result to be tested."
            )
        objective_output = objective(result)

    # check that the output has proper type and is not empty
    assert isinstance(objective_output, list), (
        "The output of the objective function should be a list of dicts by "
        "design. Please report this issue on benchopt's GitHub."
    )
    objective_output = objective_output[0]
    assert isinstance(objective_output, dict), (
        "The output of the objective function should be a dict by design. "
        "Please report this issue on benchopt's GitHub."
    )
    assert "objective_name" not in objective_output, (
        "`name` is a reserved key in the objective output dict. "
        "Please remove it from the output of the objective function."
    )
    assert len(objective_output) > 0, (
        "The output of the objective function should not be an empty dict."
    )


def test_benchmark_config_validity(benchmark):
    """Check benchmark config.yml only uses valid benchmark options."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", UserWarning)
        benchmark.get_setting("plots")

    if caught:
        details = "\n".join(f"{w.message}" for w in caught)
        config_file = benchmark.get_config_file()
        pytest.fail(
            "Invalid benchmark config.yml detected while running "
            "benchopt test.\n"
            f"Benchmark config file: {config_file}\n"
            "Please update config.yml to only use valid benchmark options.\n"
            f"Reported issue(s):\n\n{details}"
        )


def test_solver_class(benchmark, solver_class):
    """Check that all installed solver_class respects the public API"""

    # Check that the solver_class exposes a name
    assert hasattr(solver_class, 'name'), "All solver should expose a name"
    assert isinstance(solver_class.name, str), (
        "The solver's name should be a string"
    )
    assert '/' not in solver_class.name, (
        f"The solver's name should not contain '/' (got "
        f"'{solver_class.name}'). A '/' makes the name ambiguous with a "
        "`-s path/to/solver.py` file selector."
    )

    # Check that the solver_class uses a valid sampling_strategy
    if solver_class.sampling_strategy is not None:
        msg = f"sampling_strategy should be in {SAMPLING_STRATEGIES}."
        assert solver_class.sampling_strategy in SAMPLING_STRATEGIES, msg

    # Check that the solver_class uses a valid stopping criterion
    if hasattr(solver_class, 'stopping_criterion'):
        assert isinstance(solver_class.stopping_criterion, StoppingCriterion), (  # noqa E501
            "stopping_criterion should be an instance of StoppingCriterion. "
            f"Got '{solver_class.stopping_criterion}'"
        )

    # Check that the solver_class uses a valid callable to override get_next.
    if hasattr(solver_class, 'get_next'):
        assert callable(solver_class.get_next), (
            "`get_next` for class Solver in "
            f"'{solver_class.__module__}' should be a callable."
        )
        # Make sure the signature is def get_next(self, int). Create instance
        # of `solver_class` then call `get_next` since it is a class method
        solver_class().get_next(0)


def test_solver_install_api(benchmark, solver_class):

    # Check that the solver_class exposes a known install cmd
    assert solver_class.install_cmd in [None, 'conda', 'shell']

    # Check that the solver_class exposes a known install cmd
    if solver_class.install_cmd == 'shell':
        assert hasattr(solver_class, 'install_script')


@pytest.mark.requires_install
def test_solver_install(test_env_name, benchmark, solver_class):

    # Make sure that the current benchmark is correctly set
    from benchopt.benchmark import Benchmark
    benchmark = Benchmark(benchmark.benchmark_dir)

    # assert that install works when forced to reinstalls
    solver_class.install(env_name=test_env_name)
    solver_class.is_installed(
        env_name=test_env_name, raise_on_not_installed=True
    )


def test_solver_stopping_criterion(benchmark, solver_class, test_dataset_name):
    # Check each solver stopping_criterion is compatible with the objective

    # instanciate dataset and objective, taking into account the test_config
    dataset_class = benchmark.get_test_dataset(name=test_dataset_name)
    objective_class = benchmark.get_benchmark_objective()
    config = get_configs(dataset_class, objective_class, solver_class)[0]

    objective = objective_class.get_instance(**config['objective'])

    # The criterion can come from the objective. The solver is not
    # initialized, as `__init__` can need its requirements.
    solver = solver_class.__new__(solver_class)
    with RunContext(objective=objective, solver=solver):
        stopping_criterion = solver.get_current('_stopping_criterion')

    # check that stopping_criterion has the proper type
    assert isinstance(stopping_criterion, StoppingCriterion), (
        "The solver's stopping_criterion should be an instance of "
        "StoppingCriterion."
    )

    # Check that if a key_to_monitor is specified, the objective returns it
    if stopping_criterion.key_to_monitor is not None:
        key = stopping_criterion.key_to_monitor_
        assert key.startswith('objective_'), (
            "The solver's stopping_criterion key_to_monitor should start with "
            "'objective_'."
        )

        # ensure classes calling `get_seed` work properly.
        dataset = dataset_class.get_instance(**config['dataset'])
        with RunContext(
            objective=objective, dataset=dataset, solver=solver_class.name,
            repetition=0, base_seed=benchmark.seed
        ):
            objective._load_data()
            result = objective._get_one_result()
            if result is None:
                return
            objective_output = objective(result)[0]

        requested_key = stopping_criterion.key_to_monitor
        available_keys = list(objective_output.keys())
        if not requested_key.startswith('objective_'):
            available_keys = [
                k.replace('objective_', '') for k in available_keys
            ]
        assert key in objective_output, (
            f"The solver's stopping_criterion monitors {requested_key}, but "
            "the objective does not return this key. Available keys are "
            f"{available_keys}."
        )


def test_solver_run(
        benchmark, solver_class, test_dataset_name, require_solver_installed
):
    # Check that the solver runs on at least one ``test_parameters`` config
    # of the resolved test dataset. If every config is incompatible, skip this
    # dataset. Note that if all datasets are skipped for one solver, the test
    # are failed and report how to setup a test dataset.
    dataset_class = benchmark.get_test_dataset(name=test_dataset_name)
    objective_class = benchmark.get_benchmark_objective()
    configs = get_configs(dataset_class, objective_class, solver_class)

    reasons = []
    for config in configs:
        dataset = dataset_class.get_instance(**config['dataset'])
        objective = objective_class.get_instance(**config['objective'])
        solver = solver_class.get_instance(**config['solver'])
        with RunContext(
            objective=objective, dataset=dataset, solver=solver,
            repetition=0, base_seed=benchmark.seed
        ):
            for component in [dataset, objective, solver]:
                reason = component._skip_reason()
                if reason is not None:
                    reasons.append(reason)
                    break
            else:
                objective._load_data()
                solver._set_objective(objective)
                _test_solver_one_objective(solver, objective)
                return

    reasons = sorted(set(reasons))
    if len(reasons) == 1:
        pytest.skip(reasons[0])
    pytest.skip("No compatible config: " + "; ".join(reasons))


def test_eval_parameters(benchmark):
    # Each entry of `eval_parameters` must be a parameter of its component.
    components = [benchmark.get_benchmark_objective()]
    components += benchmark.get_datasets() + benchmark.get_solvers()
    for component in components:
        unknown = set(component.eval_parameters) - set(component.parameters)
        assert not unknown, (
            f"{component.name}.eval_parameters lists {sorted(unknown)}, which "
            f"are not in its parameters {sorted(component.parameters)}."
        )


class _EveryCallCriterion:
    """Score the solver at each callback call, and stop after a few calls."""

    def __init__(self, n_points):
        self.n_points = n_points

    def init_stop_val(self):
        return 0

    def should_stop(self, stop_val, objective_list):
        done = stop_val + 1 >= self.n_points
        return done, 'done' if done else 'running', stop_val + 1


def _run_from_checkpoints(benchmark, config, classes, checkpoint_base, mode):
    """Run a callback solver like `run_one_to_cvg`, with fresh components.

    The solver is scored at each callback call, so that a short test run
    stores several checkpoints. Return the scores and times of the curve.
    """
    dataset_class, objective_class, solver_class = classes
    dataset = dataset_class.get_instance(**config['dataset'])
    objective = objective_class.get_instance(**config['objective'])
    solver = solver_class.get_instance(**config['solver'])
    ctx = RunContext(
        objective=objective, dataset=dataset, solver=solver, repetition=0,
        base_seed=benchmark.seed, checkpoint_base=checkpoint_base,
        checkpoint_mode=mode,
    )
    with ctx:
        objective._load_data()
        solver._set_objective(objective)
        callback = _Callback(
            objective, solver, {}, _EveryCallCriterion(n_points=4), ctx
        )
        solver.pre_run_hook(callback)
        if callback.restore():
            callback.start()
            solver.run(callback)
        ctx.checkpoint = None
        curve, _, _ = callback.get_results()
        folder = ctx.checkpoint_path / 'callback'
    scores = [
        {k: v for k, v in row.items()
         if k == 'stop_val' or (k.startswith('objective_')
                                and isinstance(v, (int, float)))}
        for row in curve
    ]
    return scores, [row['time'] for row in curve], folder


def test_solver_checkpoint(
        benchmark, solver_class, test_dataset_name, require_solver_installed,
        tmp_path
):
    # A solver that gives checkpoints to its callback must restart from them:
    # rescoring the stored points gives the same scores, and a run resumed
    # from an early point gives the same curve as an uninterrupted one.
    dataset_class = benchmark.get_test_dataset(name=test_dataset_name)
    objective_class = benchmark.get_benchmark_objective()
    config = get_configs(dataset_class, objective_class, solver_class)[0]
    if solver_class.sampling_strategy != 'callback':
        pytest.skip("Checkpoints are only stored for callback solvers.")
    classes = dataset_class, objective_class, solver_class

    ref, ref_time, folder = _run_from_checkpoints(
        benchmark, config, classes, tmp_path, 'resume'
    )
    points = sorted(
        int(f.stem[len('point_'):]) for f in folder.glob('point_*.pkl')
    )
    if not points:
        pytest.skip("The solver gives no checkpoint to its callback.")
    assert points == [row['stop_val'] for row in ref], (
        "Each scored point should have a checkpoint: call the callback "
        "after the last step instead of returning before it."
    )

    # Rescoring evaluates each stored checkpoint again, without training.
    rescored, rescored_time, _ = _run_from_checkpoints(
        benchmark, config, classes, tmp_path, 'rescore'
    )
    assert rescored == ref, (
        "Scores differ when the stored checkpoints are evaluated again. "
        "Check that the checkpoint holds all the state used by get_result, "
        "that get_result is deterministic, and that the first callback call "
        "happens before the first step."
    )
    assert rescored_time == ref_time

    if len(points) < 3:
        return
    # Remove all but the 2 first points, as if the run had been interrupted.
    for f in folder.glob('*.pkl'):
        if not (f.stem.startswith('point_')
                and int(f.stem[len('point_'):]) in points[:2]):
            f.unlink()
    resumed, resumed_time, _ = _run_from_checkpoints(
        benchmark, config, classes, tmp_path, 'resume'
    )
    assert [r['stop_val'] for r in resumed] == points
    for row, ref_row in zip(resumed, ref):
        assert row == pytest.approx(ref_row, rel=1e-5), (
            "The run resumed from a checkpoint differs from the "
            "uninterrupted one. Check that the checkpoint holds the full "
            "training state: model, optimizer, schedule, step and RNG."
        )
    assert resumed_time == sorted(resumed_time)
    shutil.rmtree(tmp_path, ignore_errors=True)


def _test_solver_one_objective(solver, objective):
    # Test a solver runs with a given objective and give proper result.

    is_convex = getattr(objective, "is_convex", False)

    if solver.get_current('_sampling_strategy') in ['iteration', 'callback']:
        stop_val = 5000 if is_convex else 2
    else:
        stop_val = 1e-10 if is_convex else 1e-2
    solver.run_once(stop_val)

    # Check that returned results are compatible with the objective
    result = solver.get_result()
    objective(result)

    # Only check optimality or convex problems, when solver only return
    # one value, which is a np.array
    if (is_convex and len(result) == 1
            and isinstance(list(result.values())[0], np.ndarray)):
        key = list(result.keys())[0]
        arr = result[key]
        val_star = objective(result)['objective_value']
        for _ in range(100):
            eps = 1e-5 * np.random.randn(*arr.shape)
            val_eps = objective({key: arr + eps})['objective_value']

            diff = val_eps - val_star
            assert diff >= 0


##############################################################################
# --- Utilities to test the CLI commands ----------------------------------- #
##############################################################################


@pytest.fixture(autouse=True)
def check_test(request):

    if 'benchmark' not in request.fixturenames:
        raise ValueError(
            '`check_test` fixture should only be used in tests parametrized '
            'with `benchmark` fixture'
        )

    benchmark = request.getfixturevalue('benchmark')
    test_config_file = benchmark.get_test_config_file()
    if test_config_file is None:
        return None
    test_config_module = _get_module_from_file(
        test_config_file, benchmark.benchmark_dir
    )
    check_func_name = f"check_{request.function.__name__}"
    check_func = getattr(test_config_module, check_func_name, None)
    if check_func is None and request.function.__name__ == "test_solver_run":
        # Backward compatibility for benchmarks before benchopt 1.7.1
        check_func = getattr(test_config_module, "check_test_solver", None)
        if check_func is not None:
            warn_msg = (
                "The function `check_test_solver` is deprecated since "
                "benchopt 1.7.1. Please rename it to `check_test_solver_run`."
            )
            pytest.warns(DeprecationWarning, match=warn_msg)
    if check_func is not None:
        requires = inspect.signature(check_func).parameters
        check_func(
            **{
                f: request.getfixturevalue(
                    f"{f}_class" if f in ['dataset', 'solver', 'objective']
                    else f
                ) for f in requires
            }
        )
