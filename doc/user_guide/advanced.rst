.. _advanced_usage:

Advanced usage
==============


This page intends to list some advanced functionality
to make it easier to use the benchmark.

.. _skipping_solver:

Skipping a solver for a given problem
-------------------------------------

Some solvers might not be able to run with all the datasets present
in a benchmark. This is typically the case when some datasets are
represented using sparse data or for datasets that are too large.

In these cases, a solver can be skipped by implementing the method
:func:`~benchopt.BaseSolver.skip`, which receives the objective and the
dataset of the run. It returns a string giving the reason to skip the
solver, displayed in the output, or ``None`` to run it. Any other value
raises an error, as it is most likely a bug in ``skip``. Similarly,
:func:`~benchopt.BaseObjective.skip` receives the dataset and skips the
runs of all solvers for this dataset, and :func:`~benchopt.BaseDataset.skip`
takes no argument and skips all the runs of the dataset, e.g. for
incompatible parameters.

They are checked before launching the runs, so a skipped configuration never
starts a job. Checks on the parameters, such as ``objective.reg`` or
``dataset.n_samples``, are free. If the check needs the data, call
``dataset.get_data()`` or ``objective.get_objective()``. The data is then
loaded on the machine running ``benchopt run``, once per dataset, as
``get_data`` is cached. For instance, for an objective with a parameter
``reg`` and a dataset giving ``X``, we get

.. code-block::

    class Solver(BaseSolver):
        ...
        def skip(self, objective, dataset):
            from scipy import sparse

            if objective.reg == 0:
                return "solver does not work with reg=0"

            # Loads the data on the node running `benchopt run`.
            if sparse.issparse(dataset.get_data()["X"]):
                return "solver does not support sparse data X."

.. note::

    In older versions, ``skip`` received the data as keyword arguments,
    e.g. ``Solver.skip(self, X, y, reg)`` with the output of
    ``Objective.get_objective``, and ``Objective.skip(self, X, y)`` with the
    output of ``Dataset.get_data``. It returned a ``(skip, reason)`` tuple.
    Both still work, with a ``FutureWarning``, and are checked before
    launching the runs, but the old signature always loads the data. They will
    be removed in benchopt 1.12.

.. _extra_objectives:

Advanced usage of ``Objective`` class
-------------------------------------

The ``Objective`` class is used to evaluate each method's result, with
a call to the ``evaluate_result`` method. This method is called with the
dictionary returned by the solver's ``get_result`` method and should
return a dictionary, whose keys/values are the names and values of the metrics.
Each solver's run constitutes a single row in the benchmark result dataframe.
For more flexibility, the ``Objective`` class can also be used to produce
multiple rows in the benchmark result dataframe at once, or to save the
final results of a solver.

.. _multiple_evaluation:

Producing multiple evaluations at once
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``evaluate_result`` method can be used to produce multiple rows in the
benchmark result dataframe. This is done by returning a list of dictionaries
instead of a single dictionary. Each dictionary in the list should be a valid
result dictionary, *i.e.*, it should not contain a ``name`` key and should
have a key that matches the ``key_to_monitor`` for the solver (see :ref:`stopping_criterion`).

This feature typically allows to store metrics for each sample in a test set
or for each fold in a cross-validation setting, allowing to compute aggregated
statistics at plotting time.

.. _save_final_results:

Saving Final Results of a Solver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using the `save_final_results(**results)` method of the objective function to
retrieve the results to save. They are saved in `outputs/final_results/` directory
and reference is added in the benchmark `.parquet` file.

.. _benchmark_utils_import:

Reusing some code in a benchmark
--------------------------------

In some situations, multiple solvers need to have access to the same
functions. As a benchmark is not structured as proper python packages
but imported dynamically to avoid installation issues, we resort to
a special way of importing modules and functions defined for a benchmark.

First, all code that needs to be imported should be placed under
``BENCHMARK_DIR/benchmark_utils/``, as described here:

.. code-block::

    my_benchmark/
    ├── objective.py  # contains the definition of the objective
    ├── datasets/
    ├── solvers/
    └── benchmark_utils/
        ├── __init__.py
        ├── helper1.py  # some helper
        └─── helper_module  # a submodule
            ├── __init__.py
            └── submodule1.py  # some more helpers

Then, these modules and packages can be imported as a regular package, i.e.,

.. code-block:: python

    from benchmark_utils import helper1
    from benchmark_utils.helper1 import func1
    from benchmark_utils.helper_module.submodule1 import func2



.. _precompilation:

Caching pre-compilation and warmup effects
------------------------------------------

For some solvers, such as solvers relying on just-in-time compilation with
``numba`` or ``jax``, the first iteration might be longer due to "warmup"
effects. To avoid having such effects in the benchmark results, it is usually
advised to call the solver once before running the benchmark. This should be
implemented in the ``Solver.warm_up`` method, which is empty by default and
called after the `set_objective` method. For solvers with
``sampling_strategy`` in ``{'tolerance',  'iteration'}``, simply calling the
``Solver.run`` with a simple enough value is usually enough. For solvers with
``sampling_strategy`` set to ``'callback'``, it is possible to call
``Solver.run_once``, which will call the ``run`` method with a simple callback
that does not compute the objective value and stops after ``n_iter`` calls to
callback (default to 1).


.. code-block:: python

    class Solver(BaseSolver):
        ...

        def warm_up(self):
            # Cache pre-compilation and other one-time setups that should
            # not be included in the benchmark timing.
            self.run(1)  # For sampling_strategy == 'iteration' | 'tolerance'
            self.run_once()  # For sampling_strategy == 'callback'


.. _data_memory:

Data loading and memory
-----------------------

Benchopt loads each dataset once and keeps its data in memory to run all the
solvers on it, which avoids reloading the data for every solver. The data is
released when the run moves to the next dataset. With ``--group-by`` (see
:ref:`run_grouping`), this only holds for the first listed axis, while the
other axes keep all their instances in memory. List the heaviest,
data-carrying axis (usually ``dataset``) first.

Solvers with a costly setup, such as the warmup described above, can also
benefit from sharing in parallel runs. ``--group-by solver`` runs each solver
on all datasets in the same worker, at the cost of keeping all the datasets'
data in that worker's memory.


.. |update_params| replace:: ``update_parameters``
.. _update_params: https://github.com/facebookincubator/submitit/blob/main/submitit/slurm/slurm.py#L386

.. |SlurmExecutor| replace:: ``submitit.SlurmExecutor``
.. _SlurmExecutor: https://github.com/facebookincubator/submitit/blob/main/submitit/slurm/slurm.py#L214
