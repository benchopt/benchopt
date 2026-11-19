import ast
import sys
import uuid
import inspect

import pytest
from joblib import Parallel, delayed

from benchopt.cli.main import run as run_cmd
from benchopt.cli.main import install as install_cmd
from benchopt.utils.dynamic_modules import FailedImport
from benchopt.utils.run_context import RunContext
from benchopt.stopping_criterion import StoppingCriterion
from benchopt.base import BaseSolver
from benchopt.utils.ast_parsing import get_class_attrs
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.temp_benchmark import DEFAULT_SOLVERS

from benchopt.tests.utils import CaptureCmdOutput
from benchopt.cli.tests.completion_cases import _test_shell_completion


def test_pickling_dynamic_module():
    # Make sure the dynamic modules can be pickled by joblib. In particular,
    # this is necessary for nested parallelism in distributed context.
    #
    # This test check that the module containing a solver can be pickled, and
    # that the dynamic benchmark_utils module can be retrieved in the process.

    solver = """
    from benchopt.utils.temp_benchmark import TempSolver
    from benchmark_utils.test1 import func1

    class Solver(TempSolver):
        name = "test-solver"
        def run(self, _): func1()
    """

    with temp_benchmark(
            solvers=[solver],
            benchmark_utils={'test1': 'def func1(): print("FUNC1")'}
    ) as benchmark:
        # Get the solver from the list of tuples
        Solver, _ = benchmark.check_solver_patterns(["test-solver"])[0]
        assert Solver.is_installed()

        with CaptureCmdOutput() as out:
            Solver.run(None, None)
        out.check_output("FUNC1", repetition=1)

        # This will fail if the benchmark_utils module is not pickled by value
        # by cloudpickle.
        with CaptureCmdOutput():
            Parallel(n_jobs=2)(
                delayed(Solver.run)(None, None) for _ in range(2)
            )


def test_get_module_from_file_no_duplicate(tmp_path):
    # Loading the same file twice reuses the cached module (no duplicate),
    # while two different files with the same stem get distinct modules.
    from benchopt.utils.dynamic_modules import _get_module_from_file

    bench_dir = tmp_path / f"bench_{uuid.uuid4().hex}"
    bench_dir.mkdir()
    # Both files live outside the benchmark and share the stem "ext", so they
    # map to the same semantic package name and exercise the collision guard.
    file_a, file_b = tmp_path / "a" / "ext.py", tmp_path / "b" / "ext.py"
    for path, value in [(file_a, 1), (file_b, 2)]:
        path.parent.mkdir()
        path.write_text(f"VALUE = {value}\n")

    mod_a1 = _get_module_from_file(file_a, bench_dir, subpkg="solvers")
    mod_a2 = _get_module_from_file(file_a, bench_dir, subpkg="solvers")
    mod_b = _get_module_from_file(file_b, bench_dir, subpkg="solvers")

    # Same file -> same module, loaded once (no duplicate).
    assert mod_a1 is mod_a2 and mod_a1.VALUE == 1
    # Different file, same stem -> distinct module, not a wrong reuse.
    assert mod_b is not mod_a1 and mod_b.VALUE == 2


def test_ast_replacement_no_name():
    # Test that the AST replacement works when a dynamic module is not
    # importable. In particular, this makes sure that the module filename
    # is correctly stored in the class.

    solver = """
    from benchopt import BaseSolver
    failure

    class Solver(BaseSolver):
        pass
    """
    with temp_benchmark(solvers=solver) as bench:
        # Get the solver from the list of tuples
        with pytest.warns(UserWarning, match="has no name attribute"):
            Solver, _ = bench.check_solver_patterns(["solver_0"])[0]
        assert not Solver.is_installed()
        with pytest.raises(NameError, match="'failure' is not defined"):
            Solver.is_installed(raise_on_not_installed=True)


def test_ast_replacement_name_undefined():
    # Test that the AST replacement works when a dynamic module is not
    # importable. In particular, this makes sure that the module filename
    # is correctly stored in the class.

    solver = """
    from benchopt import BaseSolver
    failure

    class Solver(BaseSolver):
        name = undefined
    """
    with temp_benchmark(solvers=solver) as bench:
        # Get the solver from the list of tuples
        Solver, _ = bench.check_solver_patterns(["solver_0"])[0]
        assert not Solver.is_installed()
        with pytest.raises(AttributeError) as excinfo:
            Solver.is_installed(raise_on_not_installed=True)
        assert "Could not evaluate the name" in str(excinfo.value)
        assert "'failure' is not defined" in str(excinfo.value.__cause__)


@pytest.mark.parametrize("params", [
    # undefined install_cmd
    "install_cmd = undefined",
    # undefined requirements
    "requirements = undefined",
    # failing requirements
    "requirements = ['', f'{undefined}']",
])
def test_ast_replacement(params):
    # Test that the AST replacement works when a dynamic module is not
    # importable. In particular, this makes sure that the module filename
    # is correctly stored in the class.

    solver = f"""
    from benchopt.utils.temp_benchmark import TempSolver
    failure

    class Solver(TempSolver):
        name = 'my-solver'
        {params}
    """

    component = params.split('=')[0].strip()

    with temp_benchmark(solvers=solver) as bench:
        Solver, _ = bench.check_solver_patterns(["my-solver"])[0]
        assert not Solver.is_installed(quiet=True)
        with pytest.raises(NameError, match="'failure' is not defined"):
            Solver.is_installed(raise_on_not_installed=True)

        with pytest.raises(AttributeError) as excinfo:
            print(Solver.requirements, Solver.install_cmd)

        assert "Could not evaluate statically" in str(excinfo.value)
        assert "solver_0.py" in str(excinfo.value)
        assert f"'{component}'" in str(excinfo.value)


def test_ast_replacement_inherited_methods():
    # The methods of a solver that cannot be imported can come from a base
    # class, unknown to the AST replacement. It must still be possible to
    # create an instance, e.g. to get its stopping criterion in
    # `benchopt test`.
    solver = """
    from benchopt.utils.temp_benchmark import TempSolver
    failure

    class Solver(TempSolver):
        name = 'my-solver'
    """
    with temp_benchmark(solvers=solver) as bench:
        Solver, _ = bench.check_solver_patterns(["my-solver"])[0]
        assert isinstance(Solver, FailedImport)
        objective = bench.get_benchmark_objective().get_instance()
        solver = Solver.__new__(Solver)
        with RunContext(objective=objective, solver=solver):
            criterion = solver.get_current('_stopping_criterion')
        assert isinstance(criterion, StoppingCriterion)


BASE_SOLVER = """
    from benchopt.utils.temp_benchmark import TempSolver

    class MyBase(TempSolver):
        requirements = ['pip::base-req']
        parameters = {'lr': [0.1]}
"""


@pytest.mark.parametrize("import_style", [
    "from", "safe_import", "module", "reexport", "star", "assign", "local"
])
def test_ast_replacement_inherited_attributes(import_style):
    # The AST replacement collects the attributes of the bases defined in
    # the benchmark, e.g. the requirements of a base in benchmark_utils.
    utils = {"base": BASE_SOLVER}
    base = "MyBase"
    if import_style == "from":
        imports = "from benchmark_utils.base import MyBase"
    elif import_style == "safe_import":
        imports = (
            "from benchopt import safe_import_context\n"
            "    with safe_import_context() as import_ctx:\n"
            "        from benchmark_utils.base import MyBase"
        )
    elif import_style == "module":
        imports, base = "import benchmark_utils.base as bu", "bu.MyBase"
    elif import_style in ["reexport", "star"]:
        imports = "from benchmark_utils import MyBase"
        name = "MyBase" if import_style == "reexport" else "*"
        utils["__init__"] = f"from .base import {name}"
    elif import_style == "assign":
        utils["other"] = "class Other:\n    requirements = ['other']"
        imports = (
            "from benchmark_utils.other import Other as MyBase\n"
            "    from benchmark_utils.base import MyBase as Base\n"
            "    MyBase = Base"
        )
    else:
        imports, utils = inspect.cleandoc(BASE_SOLVER), None
        imports = imports.replace("\n", "\n    ")

    solver = f"""
    {imports}
    failure

    class Solver({base}):
        name = 'my-solver'
        parameters = {{'lr': [0.2]}}
    """

    with temp_benchmark(solvers=solver, benchmark_utils=utils) as bench:
        Solver, _ = bench.check_solver_patterns(["my-solver"])[0]
        assert isinstance(Solver, FailedImport)
        assert Solver.requirements == ['pip::base-req']
        assert Solver.parameters == {'lr': [0.2]}


def test_ast_replacement_unreadable_base():
    # A class re-exported from a module that cannot be parsed is reported as
    # not found, without breaking the listing of the other solvers.
    solver = """
    from benchmark_utils.broken import Solver
    """
    with temp_benchmark(
        solvers={"solver_0.py": solver, **DEFAULT_SOLVERS},
        benchmark_utils={"broken": "def broken(:"},
    ) as bench:
        Solver, _ = bench.check_solver_patterns(["solver_0"])[0]
        assert isinstance(Solver, FailedImport)
        with pytest.raises(ValueError, match="Could not find Solver"):
            Solver.is_installed(raise_on_not_installed=True)
        bench.check_solver_patterns(["test-solver"])


def test_get_class_attrs_mro():
    # Attributes follow the MRO, which is Solver, B, B, C, A, Mixin here. The
    # local `B` shadows the imported one, which is its base.
    utils = {"base": """
        class Mixin:
            install_cmd = 'Mixin'
            unknown = 'Mixin'

        class A(Mixin):
            requirements = 'A'
            parameters = 'A'
            test_config = 'A'

        class B(A):
            requirements = 'B'

        class C(A, Mixin):
            requirements = 'C'
            parameters = 'C'
            install_cmd = 'C'
    """}
    solver = """
    from benchmark_utils.base import A, B, C, Mixin

    class B(B):
        def run(self, _): pass

    class Solver(B, C, Mixin):
        parameters = undefined
    """
    with temp_benchmark(solvers=solver, benchmark_utils=utils) as bench:
        attrs = get_class_attrs(
            bench.benchmark_dir / "solvers" / "solver_0.py", BaseSolver,
            bench.benchmark_dir
        )
    # Only the attributes of `BaseSolver` are collected.
    assert set(attrs) == {
        'install_cmd', 'requirements', 'parameters', 'test_config', 'run'
    }
    assert isinstance(attrs.pop("run"), ast.FunctionDef)
    assert isinstance(attrs.pop("parameters"), AttributeError)
    assert attrs == {
        'install_cmd': 'C', 'requirements': 'B', 'test_config': 'A'
    }


@pytest.mark.parametrize("params", [
    # no name
    "pass",
    # undefined name
    "name = undefined",
    # undefined install_cmd
    "name = 'my-solver'\n        install_cmd = undefined",
    # undefined requirements
    "name = 'my-solver'\n        requirements = undefined",
    # failing requirements
    "name = 'my-solver'\n        requirements = ['', f'{undefined}']",
], ids=["no name", "undefined name", "undefined install_cmd",
        "undefined requirements", "failing requirements",])
def test_ast_failures_dont_block_run(params, no_raise_install, fake_conda_env):
    solver = f"""
    from benchopt.utils.temp_benchmark import TempSolver
    failure

    class Solver(TempSolver):
        {params}
    """

    invalid_component = params.splitlines()[-1].split("=")[0].strip()
    if invalid_component == "pass":
        invalid_component = "name"

    # Check that the failing solver does not prevent other solvers to be run.
    with temp_benchmark(solvers=[*DEFAULT_SOLVERS.values(), solver]) as bench:
        run_cmd(
            f"{bench.benchmark_dir} -s test-solver --no-plot".split(),
            'benchopt', standalone_mode=False
        )

        # Check that completion also works
        expected_solvers = (
            ['test-solver', 'solver_1'] if 'my-solver' not in params
            else ['my-solver', 'test-solver']
        )
        _test_shell_completion(
            run_cmd, f"{bench.benchmark_dir} -s".split(),
            [("", expected_solvers)]
        )

        for args in ["-s test-solver", "--minimal", ""]:
            exit_code = 1 if not args else None
            with CaptureCmdOutput(exit=exit_code) as out:
                install_cmd(
                    f"{bench.benchmark_dir} -y {args}".split(),
                    'benchopt', standalone_mode=False
                )
            print(out.raw_output)
            if args:
                out.check_output("No new requirements installed")
            else:
                if invalid_component == "name":
                    out.check_output("solver_1: collected ✓")
                    out.check_output(r"solver_1 \(no requirements\)")
                else:
                    out.check_output("my-solver: failed to get requirements ✗")
                    out.check_output(f"invalid {invalid_component}")


@pytest.mark.parametrize("safe_import", [True, False])
def test_reload_class_after_install(tmp_path, safe_import):
    # When installing in the current env, the classes have already been
    # imported, and the failed ones are `FailedImport` classes, whether the
    # import failure was caught by a `safe_import_context` or not. Check that
    # reloading them detects the requirements installed after this first
    # import.

    # This package is not installed yet, and is only made importable once the
    # benchmark has been collected.
    pkg = f"missing_pkg_{uuid.uuid4().hex[:8]}"
    if safe_import:
        import_pkg = (
            "with safe_import_context() as import_ctx:\n"
            f"        import {pkg}"
        )
    else:
        import_pkg = f"import {pkg}"

    solver = f"""
    from benchopt import safe_import_context
    from benchopt.utils.temp_benchmark import TempSolver

    {import_pkg}

    class Solver(TempSolver):
        name = "test-solver"
    """

    with temp_benchmark(solvers=[solver]) as bench:
        Solver, _ = bench.check_solver_patterns(["test-solver"])[0]
        assert isinstance(Solver, FailedImport)
        assert not Solver.is_installed(quiet=True)

        # Install the missing package in the current env.
        (tmp_path / f"{pkg}.py").write_text("")
        sys.path.insert(0, str(tmp_path))
        try:
            # Without a reload, the import failure hides the install.
            assert not Solver.is_installed(quiet=True)
            # Reloading re-imports the class and detects the install.
            assert Solver.is_installed(reload=True)
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop(pkg, None)
