.. _extend_benchmark:

Extend an existing benchmark
=============================

This page explains how to contribute to an existing benchmark by adding a new
solver, a new dataset, or a new evaluation metric.

.. note::

    The examples below are based on :ref:`minimal benchmark <get_started>`
    whose objective minimises :math:`\|X - \hat{X}\|` over matrices.
    Replace the variable names and logic with whatever the benchmark you are
    working on actually uses.

Common class attributes
-----------------------

All benchopt concept classes (:class:`~benchopt.BaseObjective`,
:class:`~benchopt.BaseDataset`, and :class:`~benchopt.BaseSolver`) share some
common class attributes that can be used to select them and specify their
behavior. These attributes include:

- ``name``: human-readable identifier used to filter them in the CLI and to
  identify the results in tables and plots.
- ``parameters``: dictionary that defines the parameter grid for that class.
  Benchopt runs the cartesian product of the listed values. The selected
  values are available as attributes (e.g., ``self.lr``, ``self.n_samples``).
  See :ref:`parametrized` for advanced formats.
- ``requirements``: list of dependencies needed for the class.
  Conda packages are listed as-is (``"numpy"``), PyPI packages are prefixed
  with ``"pip::"``, and conda channel packages can be specified with
  ``"channel::package"``. See :ref:`specify_requirements` for more details.

For instance:

.. code-block:: python

        class Solver(BaseSolver):
                parameters = {"lr": [1e-3, 1e-2]}
                name = "my-solver"
                requirements = [
                    "my_package", "pip::my_pip_package",
                    "conda_channel::my_channel_package"
                ]


.. _add_solver:

Adding a solver
---------------

Create a new Python file in the ``solvers/`` directory:

.. code-block:: bash

    my_benchmark/
    └── solvers/
        └── my_solver.py   ← new file

The file must define a class named ``Solver`` that inherits from
:class:`benchopt.BaseSolver`.

.. code-block:: python
    :caption: my_benchmark/solvers/my_solver.py

    from benchopt import BaseSolver

    import numpy as np

    class Solver(BaseSolver):
        name = "my-solver"
        parameters = {"lr": [1e-3, 1e-2]}

The new solver is automatically discovered by benchopt once the file is saved.

Required methods
~~~~~~~~~~~~~~~~

**1. set_objective** (:meth:`~benchopt.BaseSolver.set_objective`): called
once before timing starts. It receives the dictionary returned by
:meth:`~benchopt.BaseObjective.get_objective` and should store whatever
the solver needs, or setup the solver's internal state which should not be
timed:

.. code-block:: python

    def set_objective(self, X):
        self.X = X
        self.X_hat = np.zeros_like(X)

.. note::

    Check ``objective.py`` in the benchmark to see which keys
    :meth:`~benchopt.BaseObjective.get_objective` returns. These keys are the
    named arguments passed to ``set_objective``.

**2. run** (:meth:`~benchopt.BaseSolver.run`): the timed part of the
benchmark. Its signature depends on the ``sampling_strategy`` class attribute:

.. list-table::
     :widths: 20 30 50
     :header-rows: 1

     * - ``sampling_strategy``
       - Signature
       - Typical use
     * - ``"run_once"``
       - ``run(self, _)``
       - Single run when only a final point is needed.
     * - ``"callback"``
       - ``run(self, callback)``
       - User-controlled iteration loop; call ``callback()`` at each iteration.
     * - ``"iteration"``
       - ``run(self, n_iter)``
       - Solvers controlled by a maximum number of iterations.
     * - ``"tolerance"``
       - ``run(self, tol)``
       - Solvers controlled by a tolerance target.

For instance, in the case of an iterative solver evaluated at different numbers
of iterations with a callback, we would have:

.. code-block:: python

    sampling_strategy = "callback"
    def run(self, cb):
        while cb():
                self.X_hat -= self.lr * (self.X_hat - self.X)

Here, the callback is used to both evaluate the result (provided by
:meth:`~benchopt.BaseSolver.get_result`) and to check for convergence, without
accounting for the time needed to do so. See :ref:`iterative_solvers` for more
details on the different sampling strategies.

**3. get_result** (:meth:`~benchopt.BaseSolver.get_result`): called after
``run`` to retrieve the solution. It must return a dictionary whose keys match
the arguments of :meth:`~benchopt.BaseObjective.evaluate_result`:

.. code-block:: python

    def get_result(self):
        return dict(X_hat=self.X_hat)

.. note::

    Check the arguments of :meth:`~benchopt.BaseObjective.evaluate_result` in
    ``objective.py`` to see which keys must be returned.

    Also note that ``self.X_hat`` (or any other required variables) should
    exist at the end of ``run``, or before any call to ``callback()`` if using
    the callback sampling strategy, as it is used to evaluate the solver.

Optional features
~~~~~~~~~~~~~~~~~

**skip hook** — if the solver is incompatible with some dataset or objective
configurations, implement :meth:`~benchopt.BaseSolver.skip` to opt out. It
receives the same arguments as :meth:`~benchopt.BaseSolver.set_objective` and
should return ``(True, reason)`` to skip or ``(False, None)`` to proceed:

.. code-block:: python

    def skip(self, X):
        if X.ndim != 2:
            return True, "only 2-D matrices are supported"
        return False, None

Once the file is saved, the solver is automatically discovered by benchopt —
no registration step is needed.

.. _add_dataset:

Adding a dataset
----------------

Create a new Python file in the ``datasets/`` directory:

.. code-block:: bash

    my_benchmark/
    └── datasets/
        └── my_dataset.py   ← new file

.. code-block:: python
    :caption: my_benchmark/datasets/my_dataset.py

    from benchopt import BaseDataset

    import numpy as np

    class Dataset(BaseDataset):
        parameters = {
            "n_samples": [100, 1000],
            "n_features": [20, 100],
        }
        name = "my-dataset"
        requirements = ["numpy"]

Like solvers, the new dataset is automatically discovered by benchopt once the
file is saved.

Required method
~~~~~~~~~~~~~~~

:meth:`~benchopt.BaseDataset.get_data` must be implemented. It returns a
dictionary whose keys become the keyword arguments passed to
:meth:`~benchopt.BaseObjective.set_data`:

.. code-block:: python

    def get_data(self):
        X = np.load("data.npy")
        return dict(X=X)

Optional features
~~~~~~~~~~~~~~~~~

**Reproducible random data** — for simulated datasets, use
:meth:`~benchopt.BaseDataset.get_seed` to get a reproducible integer seed
that changes with the benchmark repetition:

.. code-block:: python

    def get_data(self):
        rng = np.random.default_rng(self.get_seed())
        X = rng.standard_normal((self.n_samples, self.n_features))
        return dict(X=X)

See :ref:`controlling_randomness` for more details on how to control the
randomness in the benchmark, and extra options for ``get_seed``.

.. _add_metric:

Adding a metric
---------------

Metrics are defined in the benchmark's ``objective.py`` file, in
:meth:`~benchopt.BaseObjective.evaluate_result`. They are not stored in a
separate file.

:meth:`~benchopt.BaseObjective.evaluate_result` must return a dictionary where
every key is recorded as a column in the results:

.. code-block:: python
    :caption: my_benchmark/objective.py

    def evaluate_result(self, X_hat):
        error = np.linalg.norm(self.X - X_hat)
        X_hat_norm = np.linalg.norm(X_hat)
        return dict(
            value=error,
            relative_error=error / np.linalg.norm(self.X),
            X_hat_norm=X_hat_norm,
        )

All returned keys are prefixed with ``objective_`` in the results dataframe
(e.g.  ``objective_value``, ``objective_relative_error``,
``objective_X_hat_norm``). For solvers evaluated along their convergence paths,
the ``value`` key is used to keep track of the convergence curve. This can be
tweaked, changing convergence detection and key to monitor in the stopping
criteria (see :ref:`Iterative solvers page <iterative_solvers>` for details).

.. note::

    When :meth:`~benchopt.BaseObjective.evaluate_result` returns a list of
    dictionaries, each element is stored as a separate row in the results. This
    is useful to report metrics on several sub-problems or cross-validation
    folds at once. For iterative solvers, the convergence is decided based on
    the last value of the list.

When adding a metric, make sure :meth:`~benchopt.BaseObjective.get_one_result`
still returns a dictionary compatible with the updated
:meth:`~benchopt.BaseObjective.evaluate_result` signature, as this method is
used by :ref:`benchopt test <test_benchmark>` to validate the benchmark:

.. code-block:: python

    def get_one_result(self):
        return dict(X_hat=np.zeros_like(self.X))
