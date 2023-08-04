.. _add_solver:

Add a solver to an existing benchmark
=====================================

This tutorial shows how to add a new solver to a benchmark.
We illustrate the process on the `Ridge regression benchmark <https://github.com/benchopt/benchmark_ridge>`_ by implementing ``scikit-learn`` Ridge estimator.

.. Hint::
    If not yet done, you can review the :ref:`get started page <get_started>` to learn how to install benchopt and download an existing benchmark.


Before the implementation
-------------------------

A solver is a Python class, ``Solver``, that inherits from ``benchopt.BaseSolver`` and is declared in a standalone Python file in the benchmark's ``solvers/`` folder.

First, create a new Python file ``sklearn.py`` in the ``solvers/`` directory and put inside it the following content


.. code-block:: python
    :caption: benchmark_ridge/solvers/mysolver.py

    from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = 'sklearn'

The attribute ``name`` does not have to match the file name, but it makes it easier to locate the solver.

Doing the latter steps, our benchmark folder will resemble

.. code-block:: bash

    benchmark_ridge/
    ├── objective.py     # contains the implementation of th Objective
    ├── datasets/
    │   ├── dataset1.py  # existing dataset
    │   ├ ...            # other datasets
    └── solvers/
        ├── sklearn.py   # our newly added solver
        ├ ...            # other solvers


Implementation
--------------

Once the Python file is created, we can start the implementation by adding methods and attributes to the ``Solver`` class.
To do so, we follow the order that benchopt uses to call the methods during the benchmark's run: first ``set_objective``, then ``run`` and finally ``get_result``.

.. figure:: https://raw.githubusercontent.com/benchopt/communication_materials/master/sharedimages/benchopt_schema_dependency.svg
   :align: center
   :width: 90 %

Let's go over them one by one.

Initializing the setup
~~~~~~~~~~~~~~~~~~~~~~

The first method we need to implement is ``set_objective``.
It receives all the information about the dataset and objective parameters.
This is standardized in the ``objective.py`` file of the benchmark through the ``get_objective`` method.

In the Ridge benchmark, ``get_objective`` returns a dictionary with four keys: ``X``, ``y``, ``lmbd``, and ``fit_intercept`` and therefore our ``set_objective`` must take them as input arguments.

.. code-block:: python
    :caption: benchmark_ridge/objective.py

    from benchopt import BaseObjective

    class Objective(BaseObjective):
        name = "Ridge Regression"
        ...
        def get_objective(self):
            return dict(
                X=self.X, y=self.y,
                lmbd=self.lmbd,
                fit_intercept=self.fit_intercept
            )
        ...

.. note::
    If you are working with another benchmark, check the definition of ``Objective.get_objective`` in the ``objective.py`` to see which arguments are passed to ``Solver.set_objective``.

The ``set_objective`` method is meant to store references of dataset and objective parameters.
It is also used to initialize unchanging variables across the solver run.

In our case, we store ``X``, ``y``, ``lmbd``, and ``fit_intercept`` for future use when actually running the solver.
We also use it to instantiate a Ridge estimator that will be used to perform computation of the solution.


.. code-block:: python
    :caption: solvers/sklearn.py

    class Solver(BaseSolver):
        ...
        def set_objective(self, X, y, lmbd, fit_intercept):
            # store any info needed to run the solver as class attribute
            self.X, self.y = X, y
            self.lmbd = lmbd

            # declare anything that will be used to run your solver
            self.model = sklearn.linear_model.Ridge(
                alpha=lmbd, 
                fit_intercept=fit_intercept
            )
        ...


Describing the solver run procedure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Next, we implement the ``run`` method.
The ``run`` method combined with ``sampling_strategy`` describes how the performance curves of the solver will be constructed.

.. hint::

    The :ref:`Performance curves page <performance_curves>` provides a complete guide on the way benchopt constructs performance curves, and on the different sampling strategies.

There are three possible choices for ``sampling_strategy``: **iteration**, **tolerance**, and **callback**.
We show how to implement the ``run`` method for each one of them.

- **iteration**

This sampling strategy is for solvers that can be controlled using the maximum number of iterations performed.
In this case, benchopt treats the solver as a black box and observes its behavior for different number of iterations.

Therefore, the signature of the ``run`` method is ``run(self, n_iter)`` and its implementation resembles the snippet below.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        sampling_strategy = 'iteration'
        ...

        def run(self, n_iter):
            # configure sklearn to run for n_iter
            self.model.max_iter = n_iter
            # make sure sklearn goes until n_iter
            self.model.tol = 0

            self.model.fit(self.X, self.y)

            # store reference to the solution
            self.beta = self.model.coef_
        ...

- **tolerance**

Similar to **iteration**, this sampling strategy is used for solver controlled by the tolerance on the optimization process.
In this case, the signature of the ``run`` method is ``run(self, tolerance)`` and would be implemented as follows.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        sampling_strategy = 'tolerance'
        ...

        def run(self, tolerance):
            # configure sklearn to run for tolerance
            self.model.tol = tolerance
            # configure sklearn to run until tolerance is reached
            self.model.max_iter = int(1e12)

            self.model.fit(self.X, self.y)

            # store reference to the solution
            self.beta = beta
        ...

- **callback**

One may want to code the solver themselves rather than using a black-box one.
In that case, all intermediate iterates are available, and one should use the **callback** sampling strategy.

Let's say that we no longer implement the scikit-learn solver, but instead our own implementation of Gradient Descent.
The following snippet shows how to use the callback strategy with a user-coded solver.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        sampling_strategy = 'callback'
        ...

        def run(self, callback):
            X, y = self.X, self.y
            n_features = self.X.shape[1]
            
            # init vars
            beta = np.zeros(n_features)
            step = 1 / np.linalg.norm(self.X, ord=2) ** 2

            while callback():
                # do one iteration of the solver here:
                grad = self.X.T @ (self.X @ beta - y) + self.lmbd * beta
                beta = beta - step * grad

            # at the end of while loop, store reference to the solution
            self.beta = beta
        ...


Getting the solver's results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally, we define a ``get_result`` method that is used to pass the solver's result back to the objective.
It must return a dictionary whose keys are the input arguments of ``Objective.evaluate_result``.

In the Ridge case the input of ``Objective.evaluate_result`` is ``beta``, hence we return a dictionary with a single key ``"beta"``.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        def get_result(self):
            return {'beta': self.beta}
        ...


With these methods being implemented, your solver is now ready to be run!


Specifying the solver parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your solver has hyperparameters, you can specify them by adding an attribute ``parameters``.
This attribute is a dictionary whose keys are the solver's hyperparameters.

For example, if our solver has two hyperparameters, ``stepsize`` and ``momentum``, we implement them as follows:

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        name = "mysolver"

        parameters = {
            'stepsize': [0.1, 0.5],
            'momentum': [0.9, 0.95],
        }
        ...

They are then available in the class methods as ``self.stepsize`` and ``self.momentum``.

.. note::
    When running the solver, benchopt will use all possible combinations of hyperparameter values.
    Hence, unless specified otherwise, our solver will be run 2 x 2 = 4 times.



Additional features
-------------------

Managing imports
~~~~~~~~~~~~~~~~

To help benchopt with managing solver requirements, the non-benchopt imports should be enclosed in the context manager ``safe_import_context``.

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


Specifying the solver's requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The metadata of the solver includes the required packages to run the solver.
You can list all the solver dependencies in the class attribute ``requirements``.

For example, if your solver requires ``scikit-learn``, write:

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        requirements = ['scikit-learn']
        ...

.. note::

    Benchopt install requirements with ``conda``, using ``conda-forge`` as the default channel.
    Write instead ``CHANNEL_NAME:PACKAGE_NAME`` to use another channel.
    Similarly, use ``pip:PACKAGE_NAME`` to indicate that the package should be installed via ``pip``.


Adding a solver description
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A solver description can be specified by adding docstring to the class.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        """A description of mysolver.

        For example, a bibliographic reference.
        """
        ...

.. note::

    The solver description will be available in the dashboard of results and displayed by :ref:`hovering over the solver legend item <visualize_benchmark>`.


Skipping a setup
~~~~~~~~~~~~~~~~

It may happen that a solver does not support all setups, for instance our solver might not support fitting an intercept.
Therefore, we would like to skip this setup and not impact other solvers that support it.

Benchopt exposes a :class:`~benchopt.BaseSolver.skip` hook called with the result of ``Objective.get_objective`` to decide on whether the solver is compatible with the setup.

Assume we would like to skip fitting an intercept, we check whether ``fit_intercept == True`` and return ``True``, with a reason *"mysolver does not support fitting an intercept."*.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        def skip(self, X, y, lmbd, fit_intercept):
            if fit_intercept == True:
                return True, "mysolver does not support fitting an intercept."
            else:
                return False, ""
        ...


Caching JIT-compilation
~~~~~~~~~~~~~~~~~~~~~~~

One might rely on JIT-compilation for fast numerical computation, for instance by using ``Numba`` or ``Jax``.
The latter comes with the drawback of an initial overhead in the first run.
Idealy, one would like to disregard that in the benchmark results.

To address this need, benchopt features a :class:`~benchopt.BaseSolver.warm_up`
hook called once before the actual solver run to cache JIT-compilations.

Here is how it should be implemented

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        def warm_up(self):
            # execute the solver for one iteration
        ...

.. hint::

    Head to :ref:`API references <benchopt_hooks>` page to learn about
    the other hooks of benchopt.