.. _add_solver:

Add a solver to a benchmark 
===========================

This tutorial walks you through the cornerstones of adding a new solver
to a benchmark. To this end, we will focus on adding
`skglm <https://contrib.scikit-learn.org/skglm/>`_ solver to the
`Lasso benchmark <https://github.com/benchopt/benchmark_lasso>`_.

.. Hint::

    Head to :ref:`get_started` for your first steps with benchopt.


Before the implementation
-------------------------

A solver is a Python class that lives in a standalone Python file.
It has a unique name that distinguishes it from other solvers in the benchmark.

Start by adding a new file ``skglm.py`` to the ``solvers/`` directory.
Notice that we named both the python file and the solver ``skglm``,
but we could have chosen anything else.

.. code-block:: python

    from benchopt import BaseSolver, safe_import_context

    with safe_import_context() as import_ctx:
        import numpy as np
        from skglm import Lasso

    class Solver(BaseSolver):
        name = 'skglm'

Besides, to help benchopt with managing solver requirements, we enclosed the module
imports in the context manager ``safe_import_context``, except for benchopt imports.

.. note::
    
    Benchopt uses the context manager ``safe_import_context`` to identify missing imports,
    skip uninstalled solvers, ... For more details refer to
    :class:`~benchopt.safe_import_context` documentation.


Implementation
--------------

Once the Python file created, we can start implementing the solver by adding
methods and attributes to the solver class.

- **Specifying the solver parameters**

You can specify the parameters describing the internal functioning of the solver by adding
an attribute ``parameters``. This attribute is a dictionary whose keys are the parameters
of the solver.

For ``skglm``, the Lasso estimator has arguments to specify
the working set strategy and its initial size.

.. code-block:: python

    class Solver(BaseSolver):
        ...
        parameters = {
            'ws_strategy': ['subdiff'],
            'p0': [10]
        }
        ...

.. note::

    Another way to specify the solver parameters is by defining
    the constructor ``__init__``. It should take as arguments the
    solver parameters and stores them as class attributes.

- **Initializing the setup**

Use the method ``set_objective`` to pass in the dataset and
the objective parameters to the solver. In practice, benchopt will pass in
the result of ``Objective.get_objective``.

Also, a commune use case of this method it is to define unchanging objects
to be used across the solver run.

Here we use it to store references to the dataset ``X, y``.
Also, we store the Lasso estimator as it will not change during the solver run. 

.. code-block:: python

    class Solver(BaseSolver):
        ...
        def set_objective(self, X, y, lmbd, fit_intercept):
            self.X, self.y = X, y
            alpha = lmbd / X.shape[0]

            self.lasso = Lasso(
                alpha, tol=1e-12, fit_intercept=self.fit_intercept,
                ws_strategy=self.ws_strategy, p0=self.p0
            )
        ...

- **Describing the run procedure**

The ``run`` method combined with ``sampling_strategy`` describes how the
performance curves are constructed. In particular, the ``sampling_strategy`` dictates
the input signature of ``run`` and how it will be called by benchopt.

Here we use *iteration* as a sampling strategy. Following this choice, the ``run``
will be called repetitively with an increasing number of iterations.

.. code-block:: python

    class Solver(BaseSolver):
        ...
        sampling_strategy = 'iteration'
        ...

        def run(self, n_iter):
            self.lasso.max_iter = n_iter
            self.lasso.fit(self.X, self.y)

            # store a reference to the solution
            self.coef = self.lasso.coef_
            self.intercept = self.lasso.intercept_
        ...

.. hint::

    The :ref:`Performance curves page <performance_curves>` provides a complete guide
    on performance curves and the different sampling strategies.

- **Getting the final results**

We define a ``get_result`` method to pass the ``run`` result back
to the objective. More specifically, ``get_result`` must return a dictionary
whose keys are the input arguments of ``Objective.evaluate_result``.

Here we define a method that post-process the solution based on the ``fit_intercept`` value.

.. code-block:: python

    class Solver(BaseSolver):
        ...
        def get_result(self):
            if self.fit_intercept:
                beta = np.concatenate((self.coef, self.intercept))
            else:
                beta = self.coef

            return {'beta': beta}
        ...


Specifying metadata
-------------------

The metadata of the solver includes the required packages to run the solver.
You can list all the solver dependencies in the class attribute ``requirements``.

In our case, the solver only requires ``skglm`` to function properly.

.. code-block:: python

    class Solver(BaseSolver):
        ...
        requirements = ['pip:skglm']
        ...

.. note::

    The ``conda-forge`` is the default channel in benchopt.
    Write instead ``CHANNEL_NAME::PACKAGE_NAME`` to use another channel.
    Similarly, use ``pip:PACKAGE_NAME`` to indicate that the package
    should be installed via ``pip``.


Also, the metadata includes the description of the solver. It can be specified
by adding docstring to the class.

Here we use the docstring to add a bibliographic reference to the
`skglm <https://contrib.scikit-learn.org/skglm/>`_.

.. code-block:: python

    class Solver(BaseSolver):
        """Q. Bertrand and Q. Klopfenstein and P.-A. Bannier and G. Gidel and
        M. Massias, "Beyond L1: Faster and Better Sparse Models with skglm",
        NeurIPS 2022.
        """
        ...

.. note::

    The solver description will be available in the dashboard of results
    and displayed by :ref:`hovering over the solver legend item <visualize_benchmark>`.


Refinement
----------

- **Caching JIT-compilation:**

``skglm`` relies on Numba JIT-compilation for fast numerical computation
which comes at the expense of an initial overhead in the first run.
Ideally, we would like to disregard that in the benchmark results.

To address this need, benchopt features a ``warm_up`` hook called once
before the actual solver run to cache JIT-compilations.

In our case, we define it as follows

.. code-block:: python

    class Solver(BaseSolver):
        ...
        def warm_up(self):
            self.run(1)
        ...

.. hint::

    Head to :ref:`API references <benchopt_hooks>` page to learn about
    the other hooks of benchopt.

- **Skipping a setup**

case of skipping a zero regularization

