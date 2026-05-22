.. _API_ref:

API references
==============

Here is a list of Python functions available to construct a new benchmark with
:py:mod:`benchopt`:


.. automodule:: benchopt
   :no-members:
   :no-inherited-members:

.. currentmodule:: benchopt


List of base classes:
~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   BaseObjective
   BaseDataset
   BaseSolver


.. _parametrized:

Parametrizing Objective, Dataset, and Solver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Benchmark classes can expose several configurations through a class attribute
named ``parameters``. This applies to the concrete ``Objective``, ``Dataset``,
and ``Solver`` classes that inherit from :class:`benchopt.BaseObjective`,
:class:`benchopt.BaseDataset`, and :class:`benchopt.BaseSolver`.

The expected format is a dictionary whose keys are parameter names and whose
values are lists of candidate values:

.. code-block:: python

   class Dataset(BaseDataset):
       name = "simulated"
       parameters = {
           "n_samples": [100, 1000],
           "n_features": [20, 50],
       }

``benchopt`` evaluates the cartesian product of these values. In the example
above, the dataset is instantiated for the four combinations of
``n_samples`` and ``n_features``.

For each instantiated configuration, the selected values are stored as class
attributes, so they can be accessed as ``self.n_samples``, ``self.n_features``,
and so on inside the class methods. They are also included in the displayed
name of the instance.

When some parameters should vary together instead of being combined through a
cartesian product, they can be grouped in a single key with comma-separated
parameter names. In that case, the corresponding values must be tuples with
the same arity:

.. code-block:: python

   class Dataset(BaseDataset):
       name = "simulated"
       parameters = {
           "n_samples, n_features": [(100, 20), (1000, 50)],
           "reg": [0.1, 1.0],
       }

This keeps ``n_samples`` and ``n_features`` paired together, while still
forming the cartesian product with ``reg``.

Parameters can be overridden directly from the command line when selecting an
objective, dataset, or solver:

.. prompt:: bash $

   benchopt run . \
       -o objective[reg=0.1] \
       -d simulated[n_samples=100,n_features=[20,50]] \
       -s my-solver[use_acceleration=True]

The values in brackets use Python literal syntax, so booleans, strings,
numbers, ``None``, lists, or tuples can be passed. An override can be:

- a single value, such as ``reg=0.1``;
- a list of values, such as ``n_features=[20,50]``;
- a grouped parameter selection, such as
  ``'n_samples, n_features'=[(100, 20), (1000, 50)]``.

Only the parameters specified in the selector are replaced. All unspecified
parameters keep the values defined in the class-level ``parameters``
dictionary. The resulting run configurations are then generated from the
cartesian product of the remaining values.

For more complex experiment definitions, the same parameter overrides can be
expressed in the run configuration file described in
:ref:`Run a benchmark <run_benchmark>`.

.. _benchopt_hooks:

Optional methods and hooks
~~~~~~~~~~~~~~~~~~~~~~~~~~

All benchmark classes expose optional methods to customise the workflow.
Full signatures are in the :ref:`API reference <api>`.

**BaseDataset**

- :func:`benchopt.BaseDataset.prepare`: expensive one-time preparation
  (downloads, extraction, preprocessing) cached by joblib. List parameter
  names that do not affect preparation in ``prepare_cache_ignore`` to avoid
  redundant runs. Triggered via :ref:`benchopt prepare <prepare_datasets>`.

**BaseObjective**

- :func:`benchopt.BaseObjective.skip`: called before ``set_data`` to skip
  dataset/objective combinations that are incompatible. Takes the same
  arguments as ``set_data``.

- :func:`benchopt.BaseObjective.get_one_result`: returns a dummy result dict
  used by ``benchopt test`` to validate metric computation. Optional — if not
  implemented, the test-time metric validation step is silently skipped.

- :func:`benchopt.BaseObjective.save_final_results`: called after the last
  run for each solver to persist artefacts (models, arrays, …) as a ``.pkl``
  file alongside the parquet results.

**BaseSolver**

- :func:`benchopt.BaseSolver.skip`: called before ``set_objective`` to skip
  solver/objective combinations that are incompatible. Takes the same arguments
  as ``set_objective``. Refer to :ref:`Advanced usage <skipping_solver>` for an
  example.

- :func:`benchopt.BaseSolver.warm_up`: called once before timed runs. Use
  ``Solver.run_once()`` here to absorb JIT compilation costs without
  impacting timings.

- :func:`benchopt.BaseSolver.pre_run_hook`: called before each ``run`` with
  the same ``stop_val``; useful for JAX precompilation over varying iteration
  counts.

- :func:`benchopt.BaseSolver.get_next`: overrides the default logarithmic
  ``stop_val`` schedule. Refer to :ref:`Advanced usage <sampling_strategy>`
  for an example.



Benchopt utils
~~~~~~~~~~~~~~

.. autosummary::
   :toctree: generated/

   run_benchmark
   safe_import_context
   plotting.plot_benchmark
   datasets.simulated.make_correlated_data
   utils.profile
   results.process.merge
