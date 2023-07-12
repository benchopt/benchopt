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

:func:`benchopt.BaseObjective.skip`: hook to allow skipping configurations.
It is executed after ``get_data`` to skip if current objective is
not compatible with dataset.

:func:`benchopt.BaseSolver.skip`: hook to allow skipping configurations.
It is executed right after ``set_objective`` to skip if solver
if not compatible with objective and/or dataset parameters.
Refer to :ref:`Advanced usage <skiping_solver>` for an example.

:func:`benchopt.BaseSolver.get_next`: hook called repeatedly after ``run``
to change the sampling points for a given solver. It is called with the
previous ``stop_val`` return the next one. Refer to
:ref:`Advanced usage <sampling_strategy>` for an example

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
