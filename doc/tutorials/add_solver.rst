.. _add_solver:

Add a solver to a benchmark
===========================

This tutorial walks you through the cornerstones of adding a new solver to a benchmark.
To this end, we will focus on adding a new solver to the
`Lasso benchmark <https://github.com/benchopt/benchmark_lasso>`_.

.. Hint::

    If you have not already done it, head to :ref:`get_started` to install benchopt and clone the Lasso benchmark repository.


Before the implementation
-------------------------

A solver is a Python class, inheriting from ``benchopt.BaseSolver``, declared in a standalone Python file in the ``solvers/`` folder.

The first step is to create this file and declare the class: start by adding a new file ``mysolver.py`` to the ``solvers/`` directory, with the following content.

.. code-block:: python

    # file solvers/mysolver.py
    from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = 'mysolver'

The ``name`` variable does not have to match the name of the file, but it makes it easier to locate the solver.


Implementation
--------------

Once the Python file is created, we can start implementing the solver by adding
methods and attributes to the solver class.
We will go over them one by one.

Specifying the solver parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can specify the parameters describing the internal functioning of the solver by adding an attribute ``parameters``.
This attribute is a dictionary whose keys are the parameters of the solver.

We'll assume that the solver we're implementing has two hyperparameters, ``stepsize`` and ``momentum``.
For now, we'll define two default values for each of them.

.. code-block:: python

    class Solver(BaseSolver):
        name = "mysolver"

        parameters = {
            'stepsize': [0.1, 0.5],
            'momentum': [0.9, 0.95],
        }
        ...

.. note::
    When running the solver, benchopt will use all possible combinations of hyperparameter values.
    Hence, unless specified otherwise, our solver will be run 2 x 2 = 4 times.
..     Another way to specify the solver parameters is by defining
..     the constructor ``__init__``. It should take as arguments the
..     solver parameters and stores them as class attributes.

TODO XXX here include image of workflow.

Initializing the setup
~~~~~~~~~~~~~~~~~~~~~~

The first method we need to implement is ``set_objective``.
It receives all the information about the dataset and objective parameters.
For each benchmark, this is standardized.
Check the ``get_objective`` method of the ``Objective`` class, defined in the ``objective.py`` file of the benchmark.

In the Lasso case, ``get_objective`` returns a dictionary with 4 keys: ``X``, ``y``, ``fit_intercept`` and ``lmbd``.

The signature of ``set_objective`` should thus be ``set_objective(self, X, y, lmbd, fit_intercept)``

.. code-block:: python

    class Solver(BaseSolver):
        ...
        def set_objective(self, X, y, lmbd, fit_intercept):
            # store any info needed to run the solver as class attribute.
            self.X, self.y = X, y
            self.alpha = lmbd / X.shape[0]
            # declare anything that will be used to run your solver
        ...

Describing the solver run procedure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Next, we implement the ``run`` method.
It describes how the solver is executed on the data.
There are three possible implementations, depending on which sampling strategy is used to construct the performance curve.


The ``run`` method combined with ``sampling_strategy`` describes how the  performance curves are constructed.

.. hint::

    The :ref:`Performance curves page <performance_curves>` provides a complete guide
    on performance curves and the different sampling strategies.

There are 3 possible choices: "iteration", "tolerance", and "callback".
We show how to implement ``run`` in these three cases.

- "iteration"
This sampling strategy is for black box solvers for which one can only control the number of iterations performed.
The signature of ``run`` in that case is ``run(self, n_iter)``

.. code-block:: python

    class Solver(BaseSolver):
        ...
        sampling_strategy = 'iteration'
        ...

        def run(self, n_iter):
            w = my_black_box(self.X, self.y, self.alpha, n_iter=n_iter)
        ...

- TODO XXX do the same for tolerance and callback.

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

- "callback"

Getting the solver's results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally, we define a ``get_result`` method that is used to pass the solver's result back to the objective.
More specifically, ``get_result`` must return a dictionary whose keys are the input arguments of ``Objective.evaluate_result``.

In our case the input of ``Objective.evaluate_result`` is TODO XXX, hence we return a dict with an only key, ``"beta"``

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


Managing imports
----------------

Note that, to help benchopt with managing solver requirements, the non-benchopt imports should be enclosed in the context manager ``safe_import_context``, as follows:

.. code-block:: python

    from benchopt import BaseSolver, safe_import_context

    with safe_import_context() as import_ctx:
        import numpy as np
        # all your other import should go here

    class Solver(BaseSolver):
        name = 'mysolver'
        ...

This ``safe_import_context`` context manager is used by benchopt to identify missing imports, skip uninstalled solvers, etc.
For more details, refer to :class:`~benchopt.safe_import_context` documentation.

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

To address this need, benchopt features a :class:`~benchopt.BaseSolver.warm_up`
hook called once before the actual solver run to cache JIT-compilations.

In our case, we define it as follows

.. code-block:: python

    class Solver(BaseSolver):
        ...
        def warm_up(self):
            self.run(1)
        ...


- **Skipping a setup**

Since ``skglm`` has a scikit-learn-like API, its Lasso estimator doesn't support
zero regularization, namely the case of ``lambda=0``. Therefore, we would like to skip
this setup as other solvers might support it.

Benchopt exposes a :class:`~benchopt.BaseSolver.skip` hook called with result of
``Objective.get_objective`` to decide on whether the solver is compatible with the setup.

For ``skglm``, we skip the setup ``lambda=0`` with a reason *"skglm does not support OLS"*.

.. code-block:: python

    class Solver(BaseSolver):
        ...
        def skip(self, X, y, lmbd, fit_intercept):
            if lmbd == 0:
                return False, "skglm does not support OLS"

            return True, ""
        ...

.. hint::

    Head to :ref:`API references <benchopt_hooks>` page to learn about
    the other hooks of benchopt.
