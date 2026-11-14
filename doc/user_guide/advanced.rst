.. _advanced_usage:

Advanced usage
==============


This page intends to list some advanced functionality
to make it easier to use the benchmark.

.. _skipping_config:

Skipping a configuration
------------------------

Some configurations of a benchmark cannot run. A dataset can have incompatible
parameters, an objective might not apply to some datasets, and a solver might
not support sparse data or scale to large datasets. Each component can skip
them by implementing a ``skip`` method, which receives the components chosen
before it:

- :func:`~benchopt.BaseDataset.skip` takes no argument and skips all the runs
  of the dataset.
- :func:`~benchopt.BaseObjective.skip` receives the dataset and skips the runs
  of all solvers.
- :func:`~benchopt.BaseSolver.skip` receives the objective and the dataset.

``skip`` returns the reason to skip, displayed in the output, or ``None`` to
run. Any other value or a failing ``skip`` is reported as an error, and its
runs are not created.

The skips are checked once per configuration, before launching the runs.
Checks on the parameters are free. Calling ``dataset.get_data()`` or
``objective.get_objective()`` loads the data of the first repetition on the
machine running ``benchopt run``, once per dataset. ``get_seed`` can use the
component itself and the ones that ``skip`` receives. Other components are only
set when :ref:`group_by <run_grouping>` chooses them first.

For instance, with an objective parameter ``reg`` and a dataset giving ``X``:

.. code-block::

    class Dataset(BaseDataset):
        ...
        def skip(self):
            if self.n_features > self.n_samples:
                return "more features than samples"

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

Consecutive runs in a process reuse the same component instances. Benchopt
skips the calls whose result is already there: ``Dataset.get_data`` is not
called again for the same dataset, and ``Objective.set_data`` is not called
again for the same dataset and objective, unless their seed changes with the
repetition. ``Solver.set_objective`` and ``Solver.run`` are called for every
run. The solver instance keeps its attributes between consecutive runs, so a
solver can skip costly steps it already did, such as loading model weights.
Benchopt does not do this for the solver. Its code must check whether the
attribute is already set, for instance in ``set_objective``.

Once a run uses another component, the previous instance is released: it goes
back to its state after creation, so its data can be freed. The state of an
objective depends on its dataset, and the state of a solver on its objective
and dataset. Each process thus keeps at most one state per component, and
loads each dataset once per block of consecutive runs using it.

The order of the runs therefore decides what is reused. By default, the runs
are ordered by dataset, then objective, then solver, so each dataset is loaded
once and ``set_data`` is called once per objective. With ``--group-by`` (see
:ref:`run_grouping`), the listed axes come first. For instance,
``--group-by solver`` runs each solver on all datasets in a row, keeping the
same solver instance, but reloads each dataset for every solver.

Attributes stored on an instance during a run do not survive a release. The
warmup described above is kept, so it runs once per solver and process.


.. |update_params| replace:: ``update_parameters``
.. _update_params: https://github.com/facebookincubator/submitit/blob/main/submitit/slurm/slurm.py#L386

.. |SlurmExecutor| replace:: ``submitit.SlurmExecutor``
.. _SlurmExecutor: https://github.com/facebookincubator/submitit/blob/main/submitit/slurm/slurm.py#L214
