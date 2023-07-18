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
not in the the system one.

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

Using such option, each configuration of ``(dataset, objective, solver)`` with
unique parameters are launched as a separated job in a job-array on the SLURM
cluster. Note that by default, no limitation is used on the number of
simultaneous jobs that are run.

If ``slurm_time`` is not set in the config file, benchopt uses by default
the value of ``--timeout`` multiplied by ``1.5`` for each job.
Note that the logs of each benchmark run can be found in ``./benchopt_run/``.

As we rely on ``joblib.Memory`` for caching the results, the cache should work
exactly as if you were running the computation sequentially, as long as you have
a shared file-system between the nodes used for the computations.

.. _skipping_solver:

Skipping a solver for a given problem
-------------------------------------

Some solvers might not be able to run with all the datasets present
in a benchmark. This is typically the case when some datasets are
represented using sparse data or for datasets that are too large.

In this cases, a solver can be skipped at runtime, depending on the
characteristic of the objective. In order to define for which cases
a solver should be skip, the user needs to implement a method
:func:`~benchopt.BaseSolver.skip` in the solver class that will take
the input as the :func:`~benchopt.BaseSolver.set_objective` method.
This method should return a boolean value that evaluate to ``True``
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



.. _sampling_strategy:

Changing the strategy to grow the computational budget (:code:`stop_val`)
------------------------------------------------------------------------

Benchopt varies the computational budget by varying either the number
of iterations or the tolerance given to the method. The default policy is
to vary these two quantities exponentially between two evaluations of the
objective. However, in some cases, this exponential growth might hide some
effects, or might not be adapted to a given solver.

The way this value is changed can be specified for each solver by
implementing a ``get_next`` method in the ``Solver`` class.
This method takes as input the previous value where the objective
function has been logged, and outputs the next one. For instance,
if a solver needs to be evaluated every 10 iterations, we would have

.. code-block::

    class Solver(BaseSolver):
        ...
        def get_next(self, stop_val):
            return stop_val + 10



.. _benchmark_utils_import:

Reusing some code in a benchmark
--------------------------------

In some situations, multiple solvers need to have access to the same
functions. As a benchmark is not structured as proper python packages
but imported dynamically to avoid installation issues, we resort to
a special way of importing modules and functions defined for a benchmark.

First, all code that need to be imported should be placed under
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
.. code-block::

    from benchopt import safe_import_context

    with safe_import_context() as import_ctx:
        from benchmark_utils import helper1
        from benchmark_utils.helper1 import func1
        from benchmark_utils.helper_module.submodule1 import func2



.. _precompilation:

Caching pre-compilation and warmup effects
------------------------------------------

For some solvers, such as solver relying on just-in-time compilation with
``numba`` or ``jax``, the first iteration might be longer due to "warmup"
effects. To avoid having such effect in the benchmark results, it is usually
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


.. |update_params| replace:: ``update_parameters``
.. _update_params: https://github.com/facebookincubator/submitit/blob/main/submitit/slurm/slurm.py#L386

.. |SlurmExecutor| replace:: ``submitit.SlurmExecutor``
.. _SlurmExecutor: https://github.com/facebookincubator/submitit/blob/main/submitit/slurm/slurm.py#L214


Benchopt configuration
----------------------

Benchopt can be configured using setting files. These files can either be created directly or generated and modified using ``benchopt config``.

There are two configuration levels. The first level is the global config for the benchopt client. It contains the system-specific tweaks, the user info such as the *<GitHub token>*, and the output levels. The second level is the configuration of the benchmarks. Each benchmark can have its own config for the kind of plots it displays by default and other display tweaks.

To get the BenchOpt global config file used by the benchopt command, you can run ``benchopt config``. Using the option ``--benchmark,-b <benchmark>`` allows to display the config file for a specific benchmark. See :ref:`config_file` for more details on how the config file path is resolved.

The structure of the files follows the Microsoft Windows INI files structure and is described in :ref:`config_structure`. The available settings are listed in :ref:`config_settings`.

The value of each setting can be accessed with the CLI using ``benchopt config [-b <benchmark>] get <name>``. Similarly, the setting value can be set using ``benchopt config [-b <benchmark>] set <name> <value>``.

.. _config_file:

Config File Location
~~~~~~~~~~~~~~~~~~~~

For the global configuration file, the resolution order is the following:

1. The environment variable ``BENCHOPT_CONFIG`` is set to an existing file,
2. A file ``benchopt.ini`` in the current directory,
3. The default file is ``$HOME/.config/benchopt.ini``.

For benchmark configuration files, they are usually located in the benchmark folder, and named ``benchopt.ini``. If it does not exist, the default is to use the global config file.

.. _config_structure:

Config File Structure
~~~~~~~~~~~~~~~~~~~~~

The config files for benchopt follow the Microsoft Windows INI files structure. The global setting are grouped in a ``[benchopt]`` section:

.. code-block:: ini

    [benchopt]
    debug = true  # Activate or not debug logs
    raise_install_error = no  # Raise/ignore install error. Default is ignore.
    github_token = 0...0  # Token used to publish results on benchopt/results

For benchmark settings, they are grouped in a section with the same name as the benchmark. For a benchmark named ``benchmark_bench``, the config structure is:

.. code-block:: ini

    [benchmark_bench]
    plots =
        suboptimality_curve
        bar_chart
        objective_curve


.. _config_settings:

Config Settings
~~~~~~~~~~~~~~~

This section lists the available settings.


**Global settings**

.. autodata:: benchopt.config.DEFAULT_GLOBAL_CONFIG



**Benchmark settings**

.. autodata:: benchopt.config.DEFAULT_BENCHMARK_CONFIG


.. _config_mamba:

Using ``mamba`` to install packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When many packages need to be installed, ``conda`` can be slow or even fail to resolve the dependency graph. Using ``mamba`` can speed up this process and make it more reliable.

To use ``mamba`` instead of ``conda`` when installing benchmark requirements, it is necessary to have ``mamba`` installed in the ``base`` conda environment, *e.g.* using ``conda install -n base mamba``. Then, benchopt can be configured to use this command instead of ``conda`` by either configuring the CLI using ``benchopt config set conda_cmd mamba`` or setting the environment variable ``BENCHOPT_CONDA_CMD=mamba``.
