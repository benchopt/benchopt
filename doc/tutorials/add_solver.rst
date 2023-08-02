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

A solver is a Python class, inheriting from ``benchopt.BaseSolver``, declared in a standalone Python file in the benchmark's ``solvers/`` folder.


.. note::
    Recall that, a benchmark structure is as follows:

    .. code-block:: bash

        benchmark_lasso/
        ├── objective.py  # contains the definition of the objective
        ├── datasets/
        │   ├── dataset1.py  # some dataset
        │   └── dataset2.py  # some dataset
        └── solvers/
            ├── solver1.py  # some solver
            └── solver2.py  # some solver

First, create a new file ``mysolver.py`` in the ``solvers/`` directory and put inside it the following content

.. code-block:: python
    :caption: solvers/mysolver.py

    from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = 'mysolver'

The ``name`` attribute does not have to match the name of the file, but it makes it easier to locate the solver.


Implementation
--------------

Once the Python file is created, we can start implementing the solver by adding methods and attributes to the solver class.
Let's go over them one by one.

Specifying the solver parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can specify the solver's hyperparameters by adding an attribute ``parameters``.
This attribute is a dictionary whose keys are the solver's hyperparameters.

In our case, let's assume that our solver has two hyperparameters, ``stepsize`` and ``momentum``.
We implement them as follows:

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

Next, we move to the implementation of the three key methods a solver must define.
As a reminder, the workflow of benchopt is depicted in the figure below.
We'll implement the methods in the order in which they get called when running the benchmark: firstly ``set_objective``, then ``run`` and finally ``get_result``.

.. figure:: ../_static/benchopt_schema_dependency.svg
   :align: center
   :width: 90 %


Initializing the setup
~~~~~~~~~~~~~~~~~~~~~~

The first method we need to implement is ``set_objective``.
It receives all the information about the dataset and objective parameters.
This is standardized for all solvers in the ``get_objective`` method of the ``Objective`` class, defined in the ``objective.py`` file of the benchmark.

In the Lasso case, ``get_objective`` returns a dictionary with four keys: ``X``, ``y``, ``lmbd``, and ``fit_intercept``.
Therefore, ``set_objective`` must take as input these arguments.

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
            # mysolver.solve is the black box solver; the names of its arguments
            # may of course differ: you should adapt to your case!
            beta = mysolver.solve(self.X, self.y, self.lmbd, n_iter=n_iter)

            # store reference to the solution
            self.beta = beta
        ...

- **tolerance**

Similar to **iteration**, this sampling strategy is used for solver controlled by the tolerance on the optimization process.
In this case, the signature of the ``run`` method is ``run(self, tol)`` and would be implemented as follows.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        sampling_strategy = 'tolerance'
        ...

        def run(self, n_iter):
            # mysolver.solve is the black box solver; the names of its arguments
            # may of course differ: you should adapt to your case!
            beta = mysolver.solve(self.X, self.y, self.lmbd, tol=tol)

            # store reference to the solution
            self.beta = beta
        ...

- **callback**

This strategy can be used when the solver is not a black box, but instead exposes the intermediate values the iterates.

Here is a as snippet that illustrate how it could be implemented.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        sampling_strategy = 'callback'
        ...

        def run(self, callback):

            while callback():
                # do one iteration of the solver here:
                beta = ...

            # at the end of while loop, store reference to the solution
            self.beta = beta
        ...


Getting the solver's results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally, we define a ``get_result`` method that is used to pass the solver's result back to the objective.
It must return a dictionary whose keys are the input arguments of ``Objective.evaluate_result``.

In our case the input of ``Objective.evaluate_result`` is ``beta``, hence we return a dictionary with a single key ``"beta"``.

.. code-block:: python
    :caption: solvers/mysolver.py

    class Solver(BaseSolver):
        ...
        def get_result(self):
            return {'beta': self.beta}
        ...


With these methods being implemented, your solver is now ready to be run!


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
