.. _add_solver:

Add a solver to a benchmark 
===========================

This tutorial walks you through the cornerstones of adding a new solver
to a benchmark. To this end, we will focus on adding
`skglm <https://contrib.scikit-learn.org/skglm/>`_ solver to the
`benchmark Lasso <https://github.com/benchopt/benchmark_lasso>`_.

.. Hint::

    Head to :ref:`get_started` for your first steps with benchopt.


Before the implementation
-------------------------

A solver is a Python class that lives in a standalone Python file.
It has a unique name that distinguish it from other solvers in the benchmark.

Start by adding a new file ``skglm.py`` to the ``solvers/`` directory.
Notice that we named the python file ``skglm`` as well as the solver,
but we could have chosen anything else.

.. code-block:: python

    from benchopt import BaseSolver, safe_import_context

    with safe_import_context() as import_ctx:
        import numpy as np
        from skglm import Lasso

    class Solver(BaseSolver):
        name = 'skglm'

To help benchopt with managing solver requirements, we enclosed the module
imports in the context manager ``safe_import_context``, except benchopt imports.

.. note::
    
    Benchopt uses the context ``safe_import_context`` to identify missing imports,
    skip uninstalled solvers, ... For more details refer to
    :class:`~benchopt.safe_import_context` documentation.

Implementation
--------------

- **Specifying the solver parameters**

Define a class attribute ``parameters`` to add parameters describing the internal
functioning of the solver. This attribute is dictionary whose keys are the parameters
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
    a class constructor ``__init__`` that takes as arguments the
    solver parameters and stores them as class attributes.

- **Initializing the setup**

Use the method ``set_objective`` to pass in the dataset and the objective parameters to
the solver. Besides, it the ideal method to define unchanging object across the solver run.

Here we use it to store references to the dataset ``X, y``.
Also, we store the Lasso estimator as it will not change during the runs. 

.. code-block:: python

    class Solver(BaseSolver):
        ...
        def set_objective(self, X, y, lmbd, fit_intercept):
            self.X, self.y = X, y
            alpha = lmbd / X.shape[0]

            self.lasso = Lasso(
                alpha, tol=1e-12, fit_intercept=fit_intercept,
                ws_strategy=self.ws_strategy, p0=self.p0
            )
        ...

- **Describing the run procedure**

The ``run`` method combined with ``sampling_strategy`` describe how the
performance curves are constructed. In particular, the ``sampling_strategy`` dictates
the input signature of ``run`` and how it will be called by benchopt.

Here we use *iteration* as sampling strategy. Following this choice, the ``run``
will be called repetitively with an increasing number of iterations.

.. code-block:: python

    class Solver(BaseSolver):
        ...
        sampling_strategy = 'iteration'
        ...

        def run(self, n_iter):
            # set/fit estimator
            self.lasso.max_iter = n_iter
            self.lasso.fit(self.X, self.y)

            # store a reference to solution
            coef = self.lasso.coef_.flatten()
            if self.fit_intercept:
                coef = np.r_[coef, self.lasso.intercept_]
            self.coef = coef
        ...

.. hint::

    The :ref:`Performance curves pages <performance_curves>` provides a complete guide
    on the performance curves and the different sampling strategies.

- **Getting the final results**

We define a ``get_result`` method to pass the result of the ``run`` back
to the objective.

Here we simply define a method that returns the solution as dictionary since
we are not post processing on the solution.

.. code-block:: python

    class Solver(BaseSolver):
        ...
        def get_result(self):
            return {'beta': self.coef}


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
    Use ``CHANNEL_NAME::PACKAGE_NAME`` to use another channel.
    similarly, use ``pip:PACKAGE_NAME`` to indicate that the package
    should be installed via ``pip``.


Also, the metadata includes the description of the solver. It can be specified
by adding docstring to the solver.

Here we use the docstring to add a bibliographic reference to the package

.. code-block:: python

    class Solver(BaseSolver):
        """Q. Bertrand and Q. Klopfenstein and P.-A. Bannier and G. Gidel and
        M. Massias, "Beyond L1: Faster and Better Sparse Models with skglm",
        NeurIPS 2022.
        """
        ...

.. note::

    The solver description will be available in the dashboard of results
    and displayed by hovering over the solver legend item.

Refinement
----------

``skglm`` relies on Numba JIT-compilation for fast numerical computation
which comes at the expense of a initial overhead in the first run.
Ideally, we would like to disregard that in the benchmark results.

To address this need, benchopt features a ``warm_up`` hook that is called
once before the actual solver run.

in our case, we define it as follows

.. code-block:: python

    class Solver(BaseSolver):
        ...
        def warm_up(self):
            self.run(1)
        ...

.. hint::

    Learn about the other hooks of benchopt in the :ref:`API references <benchopt_hooks>` page.
