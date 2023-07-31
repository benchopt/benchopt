.. _add_solver:

Add a solver
============

This tutorial walks you through the cornerstones of adding a new solver
to a benchmark. To this end, we will focus on adding ``skglm`` solver to
the benchmark Lasso.

.. Hint::

    Head to :ref:`get_started` for your first steps with benchopt.


Preliminary
-----------

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

To help benchopt with the solver requirements, we enclosed the ``skglm`` module
import in the context manager ``safe_import_context``.


Implementation
--------------

- **Specifying the solver parameters**

Define a class attribute ``parameters`` to add parameters describing the internal
functioning of the solver. 

Here for ``skglm``, Lasso estimator has arguments to specify
the working set strategy and its initial size.

.. code-block:: python

    class Solver(BaseSolver):
        ...

        parameters = {
            'ws_strategy': ['subdiff', 'fixpoint'],
            'p0': [10, 100]
        }
        ...

- **Initializing the setup**

Use the method ``set_objective`` to pass in the dataset and the Objective parameters to
the solver. Besides, it the ideal method to define unchanging object across the runs of solver.

Here we use it to store references to the dataset ``X, y``.
Also we store the Lasso estimator as it won't change during the runs. 

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
the input signature of ``run``.

Here we use iteration and sampling strategy. Following this choice, the run method
will be called repetitively using an increasing number of iterations.

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

- **Getting the final results**

We define a ``get_result`` method to pass the result of the run back
to the objective.

Here we simply define a method that returns the solution as dictionary since
we are not doing any post processing on the solution.

.. code-block:: python

    class Solver(BaseSolver):
        ...

        def get_result(self):
            return {'beta': self.coef}


Metadata
--------

The metadata of the solver includes the required packages to run the solver.
you can specify them by adding a class attribute ``requirements`` and listing 
all the dependencies there

In our case, the solver only requires ``skglm`` to function properly.

.. code-block:: python

    class Solver(BaseSolver):
        ...
        requirements = ['pip:skglm']
        ...

The metadata also includes the description of the solver. It can be specified
by adding a docstring to the solver.

Here we use the docstring to add a bibliographic reference to the package

.. code-block:: python

    class Solver(BaseSolver):
        """Q. Bertrand and Q. Klopfenstein and P.-A. Bannier and G. Gidel and
        M. Massias, "Beyond L1: Faster and Better Sparse Models with skglm",
        NeurIPS 2022.
        """
        ...

Refinement
----------
- warm_up
- skip
