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

See :ref:`class_customization` for common configuration options: parameters,
dependencies, and lifecycle hooks.


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
