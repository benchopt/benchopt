.. _get_started:

Get started
===========

.. dropdown:: Installation

   .. dropdown-tagline::

        Create an isolated environment and install benchopt in minutes.
        Use the stable release by default, or switch to pre-release builds.

   The recommended way to use benchopt is within a conda environment to fully benefit from all its features.
   Hence, start by creating a dedicated conda environment and then activate it.

   .. prompt:: bash $

       conda create -n benchopt python
       conda activate benchopt

   Benchopt is available on PyPi.
   Get the **stable version** via ``pip`` by running:

   .. prompt:: bash $

       pip install -U benchopt

   This will install the command line tool to run and process the benchmark.

.. dropdown:: Run an existing benchmark

   .. dropdown-tagline::

        Clone a community benchmark and install solver/dataset requirements.
        Run one command to compare methods and open the interactive dashboard.

   Let's get the first steps with benchopt by comparing some solvers of the
   `Lasso problem <https://en.wikipedia.org/wiki/Lasso_(statistics)>`_ on the
   `Leukemia dataset <https://www.science.org/doi/10.1126/science.286.5439.531>`_.

   Start by cloning the Lasso benchmark repository and ``cd`` into it.

   .. prompt:: bash $

       git clone https://github.com/benchopt/benchmark_lasso.git
       cd benchmark_lasso

   Then, use benchopt to install the requirements for the solvers `skglm <https://contrib.scikit-learn.org/skglm/>`_,
   `scikit-learn <https://scikit-learn.org/stable/>`_, and the dataset Leukemia.

   .. prompt:: bash $

       benchopt install -s skglm -s sklearn -d leukemia

   Finally, run the benchmark:

   .. prompt:: bash $

       benchopt run . -s skglm -s sklearn -d leukemia

   .. note::

       To explore all benchopt CLI features, refer to :ref:`cli_ref`
       or run ``benchopt --help`` or ``benchopt COMMAND_NAME --help``.

   When the run is finished, benchopt automatically opens a window in your default browser and renders the results as a dashboard.

   .. figure:: ./_static/results-get-started-lasso.png
      :align: center
      :alt: Dashboard of the Lasso benchmark results

   The dashboard displays benchmark-defined metrics tracked throughout the benchmark run such as the evolution of the objective value over time.


.. dropdown:: Create your own benchmark

   .. dropdown-tagline::

      Build your own benchmark by specifying:

      - ``Dataset``: specifies how to load data,
      - ``Objective``: defines the evaluation metrics,
      - ``Solver``: implements the method to evaluate.

      This same workflow can be reused for ML, optimization, or infrastructure.

   A benchopt benchmark has three ingredients: a **dataset**, an **objective** (your metric), and one or more **solvers** (your methods).
   Each is a single Python file. Here is the minimal structure:

   .. code-block:: none

       my_benchmark/
       ├── objective.py
       ├── datasets/
       │   └── my_dataset.py
       └── solvers/
           └── my_solver.py

   The tabs below show minimal examples for three common use cases.
   Once you are ready to go further, the :ref:`benchmark_workflow` section covers
   advanced features such as parameter sweeps, cross-validation, and convergence tracking.

   .. tab-set::

      .. tab-item:: ML benchmark

         You have a dataset, a score, and methods to compare.
         This is the simplest case: each solver runs once to completion.

         **datasets/my_dataset.py**: specifies how to load data, and potentially split it into training and test sets.

         .. code-block:: python

             from benchopt import BaseDataset

             from sklearn.datasets import make_classification
             from sklearn.model_selection import train_test_split


             class Dataset(BaseDataset):
                 name = "My dataset"

                 def get_data(self):
                     # Replace with your own data loading/splitting logic
                     X, y = make_classification()
                     X_train, X_test, y_train, y_test = train_test_split(
                         X, y, test_size=0.2, random_state=0
                     )
                     # This dict can be changed to have dataloader instead
                     return dict(
                         X_train=X_train,
                         y_train=y_train,
                         X_test=X_test,
                         y_test=y_test,
                     )

         **objective.py**: defines the evaluation metric(s) to compare methods.

         .. code-block:: python

             from benchopt import BaseObjective

             class Objective(BaseObjective):
                 name = "My ML benchmark"
                 sampling_strategy = "run_once"

                 def set_data(self, X_train, y_train, X_test, y_test):
                     self.X_train, self.y_train = X_train, y_train
                     self.X_test, self.y_test = X_test, y_test

                 def get_objective(self):
                     return dict(X_train=self.X_train, y_train=self.y_train)

                 def evaluate_result(self, model):
                     return dict(test_score=model.score(self.X_test, self.y_test))

                 def get_one_result(self):
                     from sklearn.dummy import DummyClassifier
                     return dict(
                         model=DummyClassifier().fit(self.X_train, self.y_train)
                     )

         **solvers/my_solver.py**: implements the method to evaluate.

         .. code-block:: python

             from benchopt import BaseSolver

             class Solver(BaseSolver):
                 name = "My solver"

                 def set_objective(self, X_train, y_train):
                     self.X_train, self.y_train = X_train, y_train

                 def run(self, _):
                     from sklearn.linear_model import LogisticRegression
                     self.model = LogisticRegression().fit(
                         self.X_train, self.y_train
                     )

                 def get_result(self):
                     return dict(model=self.model)

         With benchopt, you also get:

         - Reproducible runs (including controlled random seeds when relevant).
         - Parallel execution of solver/dataset combinations from the CLI.
         - Standardized result collection and comparison across methods.

      .. tab-item:: Optimization benchmark

         You have an iterative solver and want to track its convergence over time.
         Benchopt will call ``run(n_iter)`` with increasing budgets and record
         the objective value at each step.

         **datasets/my_dataset.py**

         .. code-block:: python

             from benchopt import BaseDataset
             import numpy as np

             class Dataset(BaseDataset):
                 name = "My dataset"

                 def get_data(self):
                     rng = np.random.default_rng(0)
                     A = rng.standard_normal((100, 50))
                     b = rng.standard_normal(100)
                     return dict(A=A, b=b)

         **objective.py**

         .. code-block:: python

             from benchopt import BaseObjective
             import numpy as np

             class Objective(BaseObjective):
                 name = "My optimization benchmark"

                 def set_data(self, A, b):
                     self.A, self.b = A, b

                 def get_objective(self):
                     return dict(A=self.A, b=self.b)

                 def evaluate_result(self, x):
                     residual = self.A @ x - self.b
                     return dict(value=0.5 * np.dot(residual, residual))

                 def get_one_result(self):
                     return dict(x=np.zeros(self.A.shape[1]))

         **solvers/my_solver.py**

         .. code-block:: python

             from benchopt import BaseSolver
             import numpy as np

             class Solver(BaseSolver):
                 name = "Gradient descent"

                 def set_objective(self, A, b):
                     self.A, self.b = A, b
                     self.x = np.zeros(A.shape[1])

                 def run(self, n_iter):
                     grad = self.A.T @ (self.A @ self.x - self.b)
                     step = 1 / np.linalg.norm(self.A) ** 2
                     for _ in range(n_iter):
                         self.x -= step * grad

                 def get_result(self):
                     return dict(x=self.x)

         With benchopt, you also get:

         - Fair convergence comparisons using the same stopping budgets.
         - Cached datasets and validated solver/objective interfaces.
         - Automatic result aggregation and interactive plotting dashboards.

      .. tab-item:: Infrastructure benchmark

         Benchopt is not limited to ML or optimization. You can benchmark
         infrastructure components such as data loading, preprocessing,
         or serving latency. Here is an example that measures dataloader
         throughput.

         **objective.py**

         .. code-block:: python

             from benchopt import BaseObjective

             class Objective(BaseObjective):
                 name = "Dataloader throughput"
                 sampling_strategy = "run_once"

                 def set_data(self, data_size, batch_size):
                     self.data_size = data_size
                     self.batch_size = batch_size

                 def get_objective(self):
                     return dict(data_size=self.data_size, batch_size=self.batch_size)

                 def evaluate_result(self, n_samples, elapsed):
                     samples_per_second = n_samples / elapsed if elapsed > 0 else 0.0
                     return dict(
                         samples_per_second=samples_per_second,
                         elapsed=elapsed,
                     )

                 def get_one_result(self):
                     return dict(n_samples=self.data_size, elapsed=1.0)

         **datasets/my_dataset.py**

         .. code-block:: python

             from benchopt import BaseDataset

             class Dataset(BaseDataset):
                 name = "My dataset"
                 parameters = {
                     "data_size": [100_000],
                     "batch_size": [256],
                 }

                 def get_data(self):
                     return dict(
                         data_size=self.data_size,
                         batch_size=self.batch_size,
                     )

         **solvers/my_solver.py**

         .. code-block:: python

             from benchopt import BaseSolver
             import time

             class Solver(BaseSolver):
                 name = "Python generator loader"

                 def set_objective(self, data_size, batch_size):
                     self.data_size = data_size
                     self.batch_size = batch_size

                 def run(self, _):
                     start = time.perf_counter()
                     n_samples = 0

                     # Simulate iterating over batches produced by a dataloader.
                     for i in range(0, self.data_size, self.batch_size):
                         batch_end = min(i + self.batch_size, self.data_size)
                         n_samples += batch_end - i

                     elapsed = time.perf_counter() - start
                     self.result = dict(n_samples=n_samples, elapsed=elapsed)

                 def get_result(self):
                     return self.result

         With benchopt, you also get:

         - Repeated, scriptable measurements from the same command-line workflow.
         - Easy parameter sweeps (for example ``batch_size``) and side-by-side comparisons.
         - Caching of generated data and benchmark outputs to avoid unnecessary reruns.

   Then run your benchmark with:

   .. prompt:: bash $

       benchopt run my_benchmark

   .. note::

       The examples above are intentionally minimal. The full :ref:`template_benchmark_ml`
       shows additional features such as parameter sweeps, cross-validation splits,
       and dataset configuration -- all optional, but useful as your benchmark grows.


What's next?
------------

- :ref:`benchmark_workflow` — full guide to writing, running, and publishing benchmarks
- :ref:`available_benchmarks` — browse benchmarks created by the community
- :ref:`cli_ref` — complete CLI reference
