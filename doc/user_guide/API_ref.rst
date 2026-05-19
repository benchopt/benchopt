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

Benchopt run hooks
~~~~~~~~~~~~~~~~~~

``benchopt.BaseSolver`` exposes several hooks that can be implemented to customize the behavior of a solver run:

- :func:`benchopt.BaseObjective.skip`: hook to allow skipping configurations of
  objective. It is executed before ``set_data`` to skip if the current
  objective is not compatible with the dataset. It takes in the same arguments
  that are passed to ``set_data``.

- :func:`benchopt.BaseSolver.skip`: hook to allow skipping configurations of
  solver. It is executed right before ``set_objective`` to skip a solver
  if it is not compatible with objective and/or dataset parameters. It
  takes in the same arguments that are passed to ``set_objective``.
  Refer to :ref:`Advanced usage <skipping_solver>` for an example.

- :func:`benchopt.BaseSolver.get_next`: hook called repeatedly after ``run``
  to change the sampling points for a given solver. It is called with the
  previous ``stop_val`` (i.e. tolerance or number of iterations), and returns
  the value for the next run. Refer to :ref:`Advanced usage <sampling_strategy>`
  for an example.

- :func:`benchopt.BaseSolver.warm_up`: hook called once before the solver runs.
  It is typically used to cache jit compilation of solver while not accounting
  for the time needed in the timings.

- :func:`benchopt.BaseSolver.pre_run_hook`: hook called before each call to
  ``run``, with the same argument. Allows to skip certain computation that
  cannot be cached globally, such as precompilation with different number of
  iterations in for jitted ``jax`` functions.



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
