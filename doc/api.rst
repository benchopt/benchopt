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

:func:`~benchopt.BaseSolver.skip`: hook to allow skipping some configurations.
Also available for ``Dataset`` and ``Objective``.

:func:`~benchopt.BaseSolver.get_next`: hook to change the sampling points for
a given solver.


Benchopt utils
~~~~~~~~~~~~~~


.. autosummary::
   :toctree: generated/

   run_benchmark
   safe_import_context
   plotting.plot_benchmark
   datasets.simulated.make_correlated_data
   utils.profile
