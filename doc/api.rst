.. _api_documentation:

==========
Python API
==========

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

Benchopt run hooks
~~~~~~~~~~~~~~~~~~

:func:`benchopt.BaseObjective.skip`: hook to allow skipping configurations of
objective. It is passed the results of ``Dataset.get_data``, and should skip
if the current objective is not compatible with this dataset.

:func:`benchopt.BaseSolver.skip`: hook to allow skipping configurations of
solver. It is passed the results of ``set_objective``, and should skip if
the solver is not compatible with objective and/or dataset parameters.
Refer to :ref:`Advanced usage <skipping_solver>` for an example.

:func:`benchopt.BaseSolver.get_next`: hook called repeatedly after ``run``
to change the sampling points for a given solver. It is called with the
previous ``stop_val`` (i.e. tolerance or number of iterations), and returns
the value for the next run. Refer to :ref:`Advanced usage <sampling_strategy>`
for an example.

:func:`benchopt.BaseSolver.pre_run_hook`: hook called before each call to
``run``, with the same argument. Allows skipping computations that
cannot be cached globally, such as precompilation with different number of
iterations for jitted ``jax`` functions.

:func:`benchopt.BaseSolver.warm_up`: hook called once before the solver runs.
It is typically used to cache jit compilation of solver while not accounting
for the time needed in the timings.

Benchopt utils
~~~~~~~~~~~~~~


.. autosummary::
   :toctree: generated/

   run_benchmark
   safe_import_context
   plotting.plot_benchmark
   datasets.simulated.make_correlated_data
   utils.profile
