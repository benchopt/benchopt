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

Let's start by creating a new file ``mysolver.py`` in the ``solvers/`` directory and put inside it the content

.. code-block:: python
    :caption: solvers/mysolver.py

    from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = 'mysolver'

The ``name`` variable does not have to match the name of the file, but it makes it easier to locate the solver.


Implementation
--------------

Once the Python file is created, we can start implementing the solver by adding methods and attributes to the solver class.
Let's go over them one by one.

Specifying the solver parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can specify the parameters describing the internal functioning of the solver by adding an attribute ``parameters``.
This attribute is a dictionary whose keys are the parameters of the solver.

If our solver were to have two hyperparameters ``stepsize`` and ``momentum``, we would have defined their default values as follows

.. code-block:: python
    :caption: solvers/mysolver.py

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

TODO XXX here include image of workflow.

Initializing the setup
~~~~~~~~~~~~~~~~~~~~~~

The first method we need to implement is ``set_objective``.
It receives all the information about the dataset and objective parameters.
This is standardized for all solvers in the ``get_objective`` method of the ``Objective`` class, defined in the ``objective.py`` file of the benchmark.

In the Lasso case, ``get_objective`` returns a dictionary with four keys: ``X``, ``y``, ``lmbd``, and ``fit_intercept``.
Therefore, ``set_objective`` must take as input theses arguments.  

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        def set_objective(self, X, y, lmbd, fit_intercept):
            # store any info needed to run the solver as class attribute.
            self.X, self.y = X, y
            self.lmbd = lmbd

            # declare anything that will be used to run your solver
        ...

Describing the solver run procedure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Next, we implement the ``run`` method.
The ``run`` method combined with ``sampling_strategy`` describes how the performance curves of solver will be constructed.

.. hint::

    The :ref:`Performance curves page <performance_curves>` provides a complete guide
    on performance curves and the different sampling strategies.

There are three possible choices for ``sampling_strategy``: **iteration**, **tolerance**, and **callback**.
We show how to implement the ``run`` method for each one of them.

- **iteration**

This sampling strategy is for solver that can be controlled using the number of iterations performed.
In this case, benchopt treats the solver as a black box and observes its behavior for different number of iterations.

Therefore, the signature of the ``run`` method is ``run(self, n_iter)`` and its implementation resembles the snippet below.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        sampling_strategy = 'iteration'
        ...

        def run(self, n_iter):
            w = mysolver.solve(self.X, self.y, self.lmbd, n_iter=n_iter)

            # store reference to the solution
            self.w = w
        ...

- **tolerance**

Similar to **iteration**, The tolerance sampling strategy is used for solver controlled by the tolerance on the solution.
Hence in this case, the signature of the ``run`` method is ``run(self, tol)`` and would be implemented as follows.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        sampling_strategy = 'tolerance'
        ...

        def run(self, n_iter):
            w = mysolver.solve(self.X, self.y, self.lmbd, tol=tol)

            # store reference to the solution
            self.w = w
        ...

- **callback**

This strategy can be used when the solver exposes its internals, namely the intermediate values the iterates.
A typical use case of **callback** sampling strategy is when the solver cannot be treated as black box and/or when it is costly to run it constantly from scratch.

Here is a as snippet that illustrate how it could be implemented.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        sampling_strategy = 'callback'
        ...

        def run(self, callback):

            while callback():
                w = mysolver.one_iteration(self.X, self.y, self.lmbd)

            # store reference to the solution
            self.w = w
        ...


Getting the solver's results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally, we define a ``get_result`` method that is used to pass the solver's result back to the objective.
More specifically, ``get_result`` must return a dictionary whose keys are the input arguments of ``Objective.evaluate_result``.

In our case the input of ``Objective.evaluate_result`` is ``beta``, hence we return a dictionary with a single key ``"beta"``.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        def get_result(self):
            return {'beta': self.w}
        ...


Managing imports
----------------

Note that, to help benchopt with managing solver requirements, the non-benchopt imports should be enclosed in the context manager ``safe_import_context``.

.. code-block:: python
    :caption: solvers/mysolver.py
   
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

In our case, the solver only requires ``numpy`` to function properly.

.. code-block:: python
    :caption: solvers/mysolver.py    

    class Solver(BaseSolver):
        ...
        requirements = ['numpy']
        ...

.. note::

    Benchopt uses ``conda`` environement with ``conda-forge`` as the default channel.
    Write instead ``CHANNEL_NAME::PACKAGE_NAME`` to use another channel.
    Similarly, use ``pip:PACKAGE_NAME`` to indicate that the package
    should be installed via ``pip``.


Also, the metadata includes the description of the solver. It can be specified
by adding docstring to the class.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        """A description of mysolver.

        A bibliographic reference to it.
        """
        ...

.. note::

    The solver description will be available in the dashboard of results and displayed by :ref:`hovering over the solver legend item <visualize_benchmark>`.


Refinement
----------

- **Caching JIT-compilation:**

One might rely on JIT-compilation for fast numerical computation, for instance by using ``Numba`` or ``Jax``.
The latter comes with the drawback of an initial overhead in the first run.
Idealy, one would like to disregard that in the benchmark results.

To address this need, benchopt features a :class:`~benchopt.BaseSolver.warm_up`
hook called once before the actual solver run to cache JIT-compilations.

In our case, we define it as follows

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        def warm_up(self):
            # execute the solver for one iteration
        ...


- **Skipping a setup**

It happens that a solver does not support all setups, for instance our solver might not support fitting an intercept.
Therefore, we would like to skip this setup and not impact other solvers that support it.

Benchopt exposes a :class:`~benchopt.BaseSolver.skip` hook called with result of
``Objective.get_objective`` to decide on whether the solver is compatible with the setup.

Assume we would like to skip fitting an intercept, we check whether ``fit_intercept == True`` and return ``True`` accompanied with a reason *"mysolver does not support fitting an intercept."*.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        def skip(self, X, y, lmbd, fit_intercept):
            if fit_intercept == True:
                return True, "mysolver does not support fitting an intercept."

            return False, ""
        ...

.. hint::

    Head to :ref:`API references <benchopt_hooks>` page to learn about
    the other hooks of benchopt.
