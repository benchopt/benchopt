.. _advanced_usage:

Advanced usage
==============


This page intends to list some advanced functionality
to make it easier to use the benchmark.

.. _slurm_run:

Running the benchmark on a SLURM cluster
----------------------------------------

Benchopt also allows easily running the benchmark in parallel on a SLURM
cluster. To install the necessary dependencies, please run:

.. prompt:: bash $

    pip install benchopt[slurm]

    # Or for dev install
    pip install -e .[slurm]

Note that for some clusters with shared python installation, it is necessary
to call ``pip install --user`` to install the packages in the user space and
not in the system one.

.. XXX - update this to point to the submitit doc if it is created.

Using the ``--slurm`` option for ``benchopt run``, one can pass a config file
used to setup the SLURM jobs. This file is a YAML file that can contain any key
to be passed to the |update_params|_ method of |SlurmExecutor|_.
Hereafter is an example of such config file:

.. code-block:: yaml

    slurm_time: 01:00:00        # max runtime 1 hour
    slurm_gres: gpu:1           # requires 1 GPU per job
    slurm_additional_parameters:
      ntasks: 1                 # Number of tasks per job
      cpus-per-task: 10         # requires 10 CPUs per job
      qos: QOS_NAME             # Queue used for the jobs
      distribution: block:block # Distribution on the node's architectures
      account: ACC@NAME         # Account for the jobs
    slurm_setup:  # sbatch script commands added before the main job
      - '#SBATCH -C v100-16g'
      - module purge
      - module load cuda/10.1.2 cudnn/7.6.5.32-cuda-10.1 nccl/2.5.6-2-cuda

Using such options, each configuration of ``(dataset, objective, solver)`` with
unique parameters is launched as a separated job in a job-array on the SLURM
cluster. Note that by default, no limitation is used on the number of
simultaneous jobs that are run.

If ``slurm_time`` is not set in the config file, benchopt uses by default
the value of ``--timeout`` multiplied by ``1.5`` for each job.
Note that the logs of each benchmark run can be found in ``./benchopt_run/``.

``slurm_array_parallelism`` can be used to limit the number of simultaneous
jobs that are run. This is useful when the cluster has no limit on the number of
simultaneous jobs that can be run. By default, this value is not set, leaving it to
the cluster to adjust this.

As we rely on ``joblib.Memory`` for caching the results, the cache should work
exactly as if you were running the computation sequentially, as long as you have
a shared file-system between the nodes used for the computations.

.. _slurm_override:

Overriding the SLURM parameters for one solver
----------------------------------------------

You can also override the SLURM parameters for a specific solver by
defining a ``slurm_params`` attribute in the solver class. This allows to
specify a different SLURM partition, resources, or other parameters that
are specific to that solver. The parameters defined in the solver class
will override the global SLURM config defined in the config file:

.. code-block:: python

    class Solver(BaseSolver):
        """GPU-based solver that needs GPU partition and specific resources."""
        name = 'GPU-Solver'

        parameters = {...}

        # Override global SLURM config for this solver
        slurm_params = {
            'slurm_partition': 'gpu',
            'slurm_gres': 'gpu:1',
            'slurm_time': '02:00:00',
            'slurm_cpus_per_task': 8,
            'slurm_mem': '16GB',
        }

        requirements = ['torch']

        def set_objective(self, X, y):
            ...

The parameters defined in the ``slurm_params`` should be compatible with
the `submitit` library, as they are passed to the `submitit.AutoExecutor`
class. For more information on the available parameters, please refer to
the `submitit documentation <https://github.com/facebookincubator/submitit>`_.
Note that in this case, the jobs with different SLURM parameters will be
launched as one job array per configuration.

.. _skipping_solver:

Skipping a solver for a given problem
-------------------------------------

Some solvers might not be able to run with all the datasets present
in a benchmark. This is typically the case when some datasets are
represented using sparse data or for datasets that are too large.

In these cases, a solver can be skipped at runtime, depending on the
characteristic of the objective. In order to define for which cases
a solver should be skip, the user needs to implement a method
:func:`~benchopt.BaseSolver.skip` in the solver class that will take
the input as the :func:`~benchopt.BaseSolver.set_objective` method.
This method should return a boolean value that evaluates to ``True``
if the solver should be skipped, and a string giving the reason of
why the solver is skipped, for display purposes. For instance,
for a solver where the objective is set with keys `X, y, reg`,
we get

.. code-block::

    class Solver(BaseSolver):
        ...
        def skip(self, X, y, reg):
            from scipy import sparse

            if sparse.issparse(X):
                return True, "solver does not support sparse data X."

            if reg == 0:
                return True, "solver does not work with reg=0"

            return False, None

.. _extra_objectives:

Advanced usage of ``Objective`` class
-------------------------------------

The ``Objective`` class is used to evaluate each method's result, with
a call to the ``evaluate_result`` method. This method is called with the
dictionary returned by the solver's ``get_result`` method and should
return a dictionary, whose keys/values are the names and values of the metrics.
Each solver's run constitutes a single row in the benchmark result dataframe.
For more flexibility, the ``Objective`` class can also be used to produce
multiple rows in the benchmark result dataframe at once, or to save the
final results of a solver.

.. _multiple_evaluation:

Producing multiple evaluations at once
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``evaluate_result`` method can be used to produce multiple rows in the
benchmark result dataframe. This is done by returning a list of dictionaries
instead of a single dictionary. Each dictionary in the list should be a valid
result dictionary, *i.e.*, it should not contain a ``name`` key and should
have a key that matches the ``key_to_monitor`` for the solver (see :ref:`stopping_criterion`).

This feature typically allows to store metrics for each sample in a test set
or for each fold in a cross-validation setting, allowing to compute aggregated
statistics at plotting time.

.. _save_final_results:

Saving Final Results of a Solver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using the `save_final_results(**results)` method of the objective function to
retrieve the results to save. They are saved in `outputs/final_results/` directory
and reference is added in the benchmark `.parquet` file.

.. _benchmark_utils_import:

Reusing some code in a benchmark
--------------------------------

In some situations, multiple solvers need to have access to the same
functions. As a benchmark is not structured as proper python packages
but imported dynamically to avoid installation issues, we resort to
a special way of importing modules and functions defined for a benchmark.

First, all code that needs to be imported should be placed under
``BENCHMARK_DIR/benchmark_utils/``, as described here:

.. code-block::

    my_benchmark/
    ├── objective.py  # contains the definition of the objective
    ├── datasets/
    ├── solvers/
    └── benchmark_utils/
        ├── __init__.py
        ├── helper1.py  # some helper
        └─── helper_module  # a submodule
            ├── __init__.py
            └── submodule1.py  # some more helpers

Then, these modules and packages can be imported as a regular package, i.e.,

.. code-block:: python

    from benchmark_utils import helper1
    from benchmark_utils.helper1 import func1
    from benchmark_utils.helper_module.submodule1 import func2



.. _precompilation:

Caching pre-compilation and warmup effects
------------------------------------------

For some solvers, such as solvers relying on just-in-time compilation with
``numba`` or ``jax``, the first iteration might be longer due to "warmup"
effects. To avoid having such effects in the benchmark results, it is usually
advised to call the solver once before running the benchmark. This should be
implemented in the ``Solver.warm_up`` method, which is empty by default and
called after the `set_objective` method. For solvers with
``sampling_strategy`` in ``{'tolerance',  'iteration'}``, simply calling the
``Solver.run`` with a simple enough value is usually enough. For solvers with
``sampling_strategy`` set to ``'callback'``, it is possible to call
``Solver.run_once``, which will call the ``run`` method with a simple callback
that does not compute the objective value and stops after ``n_iter`` calls to
callback (default to 1).


.. code-block:: python

    class Solver(BaseSolver):
        ...

        def warm_up(self):
            # Cache pre-compilation and other one-time setups that should
            # not be included in the benchmark timing.
            self.run(1)  # For sampling_strategy == 'iteration' | 'tolerance'
            self.run_once()  # For sampling_strategy == 'callback'


.. _run_benchmark_with_py_script:

Run a benchmark using a Python script
-------------------------------------

Another way to run a benchmark is via a Python script.
Typical use-cases of that are

- Automating the run of several benchmarks
- Using ``vscode`` debugger where the python script serves as an entry point to benchopt internals

The following script illustrates running the :ref:`benchmark Lasso <run_with_config_file>`.
It assumes that the python script is located at the same level as the benchmark folder.

.. code-block:: python

    from benchopt import run_benchmark


    # run benchmark
    run_benchmark(
        benchmark_path='.',
        solver_names=[
            "skglm",
            "celer",
            "python-pgd[use_acceleration=True]",
        ],
        dataset_names=[
            "leukemia",
            "simulated[n_samples=100,n_features=20]"
        ],
    )

.. note::

    Learn more about the different parameters supported by ``run_benchmark``
    function on :ref:`API references <API_ref>`.



.. |update_params| replace:: ``update_parameters``
.. _update_params: https://github.com/facebookincubator/submitit/blob/main/submitit/slurm/slurm.py#L386

.. |SlurmExecutor| replace:: ``submitit.SlurmExecutor``
.. _SlurmExecutor: https://github.com/facebookincubator/submitit/blob/main/submitit/slurm/slurm.py#L214
