.. _how:

Advanced functionnalities in a benchmark
=========================================

This page intends to list some advanced functionnality
to make it easier to use the benchmark.

.. _skiping_solver:

Skipping a solver for a given problem
-------------------------------------

Some solvers might not be able to run with all the datasets present
in a benchmark. This is typically the case when some datasets are
represented using sparse data or for datasets that are too large.

In this cases, a solver can be skipped at runtime, depending on the
characteristic of the objective. In order to define for which cases
a solver should be skip, the user needs to implement a method
:func:`~benchopt.BaseSolver.skip` in the solver class that will take
the input as the :func:`~benchopt.BaseSolver.set_objective` method.
This method should return a boolean value that evaluate to ``True``
if the solver should be skipped, and a string giving the reason of
why the solver is skipped, for display purposes. For instance,
for a solver where the objective is set with keys `X, y, reg`,
we get

.. code-block::

    class Solver(BaseSolver):
        ...
        def skip(self, X, y, reg):
            from scipy import sparse

            if sparse.issparse(X):
                return True, "solver does not support sparse data X."

            if reg == 0:
                return True, "solver does not work with reg=0"

            return False, None



.. _sampling_strategy:

Changing the strategy to grow the :code:`stop_val`
--------------------------------------------------

By default, the number of iterations or the variation of the tolerance
between  two evaluations of the objective is exponential. However, in
some cases, this exponential growth might hide some effects, or might
not be adapted to a given solver.

The way this value is changed can be specified for each solver by
implementing the ``get_next`` method in the ``Solver`` class.
This method takes as input the previous value where the objective
function have been logged, and output the next one. For instance,
if a solver needs to be evaluated every 10 iterations, we would have

.. code-block::

    class Solver(BaseSolver):
        ...
        def get_next(self, stop_val):
            return stop_val + 10



.. _benchmark_utils_import:

Reusing some code in a benchmark
--------------------------------

In some situations, multiple solvers need to have access to the same
functions. As a benchmark is not structured as proper python packages
but imported dynamically to avoid installation issues, we resort to
a special way of importing modules and functions defined for a benchmark.

First, all code that need to be imported should be placed under
``BENCHMARK_DIR/utils/``, as described here:

.. code-block::

    my_benchmark/
    ├── objective.py  # contains the definition of the objective
    ├── datasets/
    ├── solvers/
    └── utils/
        ├── helper1.py  # some helper
        └─── helper_module  # some solver
            ├── __init__.py  # some solver
            └── submodule1.py  # some solver

Then, these modules and packages can be imported using the method
:func:`benchopt.safe_import_context.import_from`. This method
takes as input the name of the module as a string and optionally
the name of the object to load. The imported package can
either be a simple ``*.py`` file or a more complex package
with a ``__init__.py`` file. The naming convention for import
is the same as for regular import, with submodules
separated with ``.``.

.. code-block::

    from benchopt import safe_import_context

    with safe_import_context() as import_ctx:
        helper1 = import_ctx.import_from('helper1')
        func1 = import_ctx.import_from('helper1', 'func1')
        func2 = import_ctx.import_from('helper_module.submodule1', 'func2')
