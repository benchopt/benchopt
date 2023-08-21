.. _add_solver:

Add a solver to an existing benchmark
=====================================

This tutorial shows how to add a new solver to a benchmark.
We illustrate the process on the `Ridge regression benchmark <https://github.com/benchopt/benchmark_ridge>`_ by implementing a solver based on the ``scikit-learn`` Ridge estimator.

.. Hint::
    If not yet done, you can review the :ref:`get started page <get_started>` to learn how to install benchopt and download an existing benchmark.


Before the implementation
-------------------------

First, create a ``mysolver.py`` file in the ``solvers/`` directory and put inside it the following content:

.. code-block:: python
    :caption: benchmark_ridge/solvers/mysolver.py

    from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = 'mysolver'

As you can see, a solver is a Python class, ``Solver``, that inherits from ``benchopt.BaseSolver`` and is declared in a standalone Python file in the benchmark's ``solvers/`` folder.
The attribute ``name`` does not have to match the file name, but it makes it easier to locate the solver.

Doing the latter steps, our benchmark folder will resemble

.. code-block:: bash

    benchmark_ridge/
    ├── objective.py     # existing implementation of the Objective
    ├── datasets/
    │   ├── ...          # existing datasets
    └── solvers/
        ├── mysolver.py  # our newly added solver
        ├── ...          # other solvers


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
It receives all the information about the dataset and objective parameters, that the solver will need to run.
This information is standardized in the ``objective.py`` file of the benchmark, through the ``Objective.get_objective`` method.
This method is part of the objective definition and has already been implemented when the benchmark was created; we do not need to write it.

In the Ridge benchmark, the relevant information is the following:

.. code-block:: python
    :caption: benchmark_ridge/objective.py

    ...
    class Objective(BaseObjective):
        ...
        def get_objective(self):
            return dict(
                X=self.X, y=self.y,
                lmbd=self.lmbd,
                fit_intercept=self.fit_intercept
            )
        ...

We see that ``get_objective`` returns a dictionary with four keys: ``X``, ``y``, ``lmbd``, and ``fit_intercept``.
Therefore our ``set_objective`` must take them as input arguments.

.. note::
    If you are working with another benchmark, check the definition of ``Objective.get_objective`` in  ``objective.py`` to see which arguments must be passed to ``Solver.set_objective``.

The ``set_objective`` method is meant to store references of dataset and objective parameters.
It is also used to initialize unchanging variables across the solver run.

In our case, we store ``X``, ``y``, ``lmbd``, and ``fit_intercept`` to use them when we will actually run the solver.
We also use the method to instantiate a Ridge estimator that will be used to perform computation of the solution.


.. code-block:: python
    :caption: benchmark_ridge/solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        def set_objective(self, X, y, lmbd, fit_intercept):
            # store any info needed to run the solver as class attribute
            self.X, self.y = X, y

            # declare anything that will be used to run your solver
            self.model = sklearn.linear_model.Ridge(
                alpha=lmbd,
                fit_intercept=fit_intercept
            )
        ...


Defining the solver run procedure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Next, we implement the ``run`` method, and declare the ``sampling_strategy`` attribute of the solver.
Together, they define how the performance curves of the solver will be constructed.

There are three possible choices for the ``sampling_strategy`` attribute: **iteration**, **tolerance**, and **callback**.
We show how to implement the ``run`` method for each one of them.

- ``sampling_strategy = "iteration"``

This sampling strategy is for **solvers that are controlled by the maximum number of iterations they perform**.
In this case, benchopt treats the solver as a black box and observes its behavior for different number of iterations.

Therefore, the signature of the ``run`` method is ``run(self, n_iter)`` and its implementation resembles the snippet below.

.. code-block:: python
    :caption: benchmark_ridge/solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        sampling_strategy = "iteration"
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

- ``sampling_strategy = "tolerance"``

Similar to **iteration**, this sampling strategy is used for **solvers controlled by the tolerance on the optimization process**.
In this case, the signature of the ``run`` method is ``run(self, tolerance)``; it would be implemented as follows.

.. code-block:: python
    :caption: benchmark_ridge/solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        sampling_strategy = "tolerance"
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

- ``sampling_strategy = "callback"``

One may want to code the solver themselves rather than using a black-box one.
In that case, all intermediate iterates are available, and one should use the **callback** sampling strategy.

Let's say that we no longer implement the scikit-learn solver, but instead our own implementation of Gradient Descent.
The following snippet shows how to use the callback strategy with a user-coded solver.

.. code-block:: python
    :caption: benchmark_ridge/solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        sampling_strategy = "callback"
        ...

        def run(self, callback):
            X, y = self.X, self.y
            n_features = self.X.shape[1]

            # init vars
            self.beta = np.zeros(n_features)
            step = 1 / (np.linalg.norm(self.X, ord=2) ** 2 + self.lmbd)

            while callback():
                # do one iteration of the solver here:
                grad = self.X.T @ (self.X @ beta - y) + self.lmbd * beta
                self.beta -= step * grad
        ...

.. note::
    The :ref:`Performance curves page <performance_curves>` provides a complete guide on the way benchopt constructs performance curves, and on the different sampling strategies.

Getting the solver's results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally, we define a ``get_result`` method that is used to pass the solver's result back to the objective.
It must return a dictionary whose keys are the input arguments of ``Objective.evaluate_result``.

In the Ridge case the input of ``Objective.evaluate_result`` is ``beta``, hence we return a dictionary with a single key, ``"beta"``.

.. code-block:: python
    :caption: benchmark_ridge/solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        def get_result(self):
            return {'beta': self.beta}
        ...

.. note::
    If you are working with another benchmark, check the arguments of ``Objective.evaluate_result`` in ``objective.py`` to see which keys must be returned by ``Solver.get_result``.

With these methods being implemented, your solver is now ready to be run!


Specifying the solver parameters
--------------------------------

If your solver has hyperparameters, you can specify them by adding an attribute ``parameters``.
This attribute is a dictionary whose keys are the solver's hyperparameters.

For example, if our solver has two hyperparameters, ``stepsize`` and ``momentum``, we implement them as follows:

.. code-block:: python
    :caption: benchmark_ridge/solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        parameters = {
            'stepsize': [0.1, 0.5],
            'momentum': [0.9, 0.95],
        }
        ...

They are then available in the class methods as ``self.stepsize`` and ``self.momentum``.

.. note::
    When running the solver, benchopt will use all possible combinations of hyperparameter values.
    Hence, unless specified otherwise, our solver will be run 2 x 2 = 4 times.
