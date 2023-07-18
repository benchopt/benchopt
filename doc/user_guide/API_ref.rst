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


Benchopt run hooks
~~~~~~~~~~~~~~~~~~

:func:`benchopt.BaseObjective.skip`: hook to allow skipping configurations of
objective. It is executed before ``set_data`` to skip if the current
objective is not compatible with the dataset. It takes in the same arguments
that are passed to ``set_data``.

:func:`benchopt.BaseSolver.skip`: hook to allow skipping configurations of
solver. It is executed right before ``set_objective`` to skip a solver
if it is not compatible with objective and/or dataset parameters. It
takes in the same arguments that are passed to ``set_objective``.
Refer to :ref:`Advanced usage <skipping_solver>` for an example.

:func:`benchopt.BaseSolver.get_next`: hook called repeatedly after ``run``
to change the sampling points for a given solver. It is called with the
previous ``stop_val`` (i.e. tolerance or number of iterations), and returns
the value for the next run. Refer to :ref:`Advanced usage <sampling_strategy>`
for an example.

:func:`benchopt.BaseSolver.warm_up`: hook called once before the solver runs.
It is typically used to cache jit compilation of solver while not accounting
for the time needed in the timings.

:func:`benchopt.BaseSolver.pre_run_hook`: hook called before each call to
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
