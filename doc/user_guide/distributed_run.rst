
.. _parallel_run:

Distributed run with Benchopt
=============================

Benchopt allows to run benchmark computation in parallel with various backends.
This page describes how to use the different backends.

.. _joblib_backend:

Running the benchmark in parallel with ``joblib``
-------------------------------------------------

This is the easiest way to run the benchmark in parallel.
It relies on ``joblib`` and it can be used by simply specifying the number of parallel runs that can be computed simultaneously with ``--n-jobs X`` or ``-j X`` when calling ``benchopt run``.
This will run all computations on the local machine where the command is invoked.

Note that ``joblib`` tries to mitigate oversubscription by reducing the number of threads that are used in C-level parallelism -- such as in BLAS calls.
This means that these parallel runs might be slower than their sequential counterpart on the same machine, and shouldn't be compared to each other.

.. _distributed_run:

Distributed computations with ``dask`` or ``submitit``
------------------------------------------------------

Benchopt also allows distributed runs for the benchmark on various cluster infrastructure, using ``dask`` or ``submitit`` backends.
Run the following command to install the dependencies of the backend you want to use

.. tab-set::

    .. tab-item:: Dask

        .. prompt:: bash $

            pip install benchopt[dask]

    .. tab-item:: Submitit

        .. prompt:: bash $

            pip install benchopt[submitit]


Using the ``--parallel-config`` option for ``benchopt run``, one can pass a configuration file used to setup the distributed jobs.
This file is a YAML with that contains a ``backend`` key to select the used distributed backend and optionally other keys to setup this backend.
Bellow are example of configuration files for each backend.

Using such option, each configuration of ``(dataset, objective, solver)`` with
unique parameters are launched as a separated job in a job-array on the SLURM
cluster.

As we rely on ``joblib.Memory`` for caching the results, the cache should work
exactly as if you were running the computation sequentially, as long as you have
a shared file-system between the nodes used for the computations.

.. _slurm_backend:

Running on SLURM with the submitit backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the config file passed to ``--parallel-config``, you can specify the
``backend`` key to be ``submitit`` and any key to be passed to the |update_params|_ method of |SlurmExecutor|_.
Hereafter is an example of such config file:

.. code-block:: yaml
    :caption: ./config_parallel.yml

    backend: submitit
    slurm_time: 01:00:00          # max runtime 1 hour
    slurm_gres: gpu:1             # requires 1 GPU per job
    slurm_stderr_to_stdout: True  # redirect all outputs to a single log file
    slurm_additional_parameters:
      ntasks: 1                   # Number of tasks per job
      cpus-per-task: 10           # requires 10 CPUs per job
      qos: QOS_NAME               # Queue used for the jobs
      distribution: block:block   # Distribution on the node's architectures
      account: ACC@NAME           # Account for the jobs
    slurm_setup:  # sbatch script commands added before the main job
      - '#SBATCH -C v100-16g'
      - module purge
      - module load cuda/10.1.2 cudnn/7.6.5.32-cuda-10.1 nccl/2.5.6-2-cuda

Using this backend, each configuration of ``(dataset, objective, solver)`` with
unique parameters is launched as a separated job in a job-array on the SLURM
cluster. The logs of each run can be found in ``./benchopt_run/``.

The parameters defined in this config file should be compatible with
the ``submitit`` library, as they are passed to the ``submitit.AutoExecutor``
class. For more information on the available parameters, please refer to
the `submitit documentation <https://github.com/facebookincubator/submitit>`_.

Note that by default, no limitation is used on the number of
simultaneous jobs that are run, leaving the cluster to adjust this. The
``slurm_array_parallelism`` parameter can be set to limit the number of
simultaneous jobs that are run when necessary.

If ``slurm_time`` is not set in the config file, benchopt uses by default
the value of ``--timeout`` multiplied by ``1.5`` for each job.

As we rely on ``joblib.Memory`` for caching the results, the cache should work
exactly as if you were running the computation sequentially, as long as you have
a shared file-system between the nodes used for the computations.

.. _slurm_override:

Overriding the SLURM parameters for one solver or one run
---------------------------------------------------------

It is possible to override the SLURM parameters for a specific solver, or varying
them for different runs of a given solver.

To specify specific configuration for one solver, you can define a
``slurm_params`` attribute in the solver class, which specifies different
SLURM's job parameters for the solver. If you want to vary some parameters
per run, you can define them in the ``parameters`` attribute of the solver.
Note that for this to work, the parameters defined in the ``parameters``
dictionary should all be prefixed with ``slurm_`` to be recognized as parameters
for this backend.

.. code-block:: python

    class Solver(BaseSolver):
        """GPU-based solver that needs GPU partition and specific resources."""
        name = 'GPU-Solver'

        parameters = {
            ...
            'slurm_nodes': [1, 2],  # Varying number of nodes per run
        }

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

As discussed above, the parameters described here should be compatible with the
``submitit`` backend. When the benchmark is run with the ``submitit`` backend,
the global SLURM config will be updated with the parameters defined in the
``slurm_params`` attribute of the solver, and then for each run. The final
configuration used for a given run is thus obtained by merging the global SLURM
config, the solver-specific parameters, and the run-specific parameters, with
priority given to the run-specific parameters. Note that in this case, the jobs
with different SLURM parameters will be launched as one job array per
configuration.


.. _dask_backend:

Running computations on a remote Cluster using ``dask``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the config file passed to ``--parallel-config``, you can specify the
``backend`` key to be ``dask`` and any key that starts with ``dask_`` will be passed to set up the |Client|_, by removing the ``dask_`` prefix.
Hereafter is an example of such config file:

.. code-block:: yaml
    :caption: ./config_parallel.yml

    backend: dask
    dask_address: 127.0.0.1:8786

If no address is specified, a local cluster is started with the number of workers specified by ``--n-jobs``.

It is also possible to setup the remote cluster using ``coiled``.
Coiled is a library that allows setting up a dask cluster on cloud providers such as AWS and GCP.
To setup the cluster, you can simply add ``coiled_*`` keys in the config file.
These keys will be passed to create an instance of |Cluster|_, that will be used to perform computations with ``dask``:

.. code-block:: yaml
    :caption: ./config_parallel.yml

    backend: dask
    coiled_name: my-benchopt-run
    coiled_n_workers: 20
    coiled_spot_policy: spot
    coiled_use_best_zone: True
    coiled_software: benchopt/my_benchmark
    coiled_worker_vm_types: |
        n1-standard-1


.. |update_params| replace:: ``update_parameters``
.. _update_params: https://github.com/facebookincubator/submitit/blob/main/submitit/slurm/slurm.py#L386

.. |SlurmExecutor| replace:: ``submitit.SlurmExecutor``
.. _SlurmExecutor: https://github.com/facebookincubator/submitit/blob/main/submitit/slurm/slurm.py#L214

.. |Client| replace:: ``dask.Client``
.. _Client: https://distributed.dask.org/en/stable/client.html

.. |Cluster| replace:: ``coiled.Cluster``
.. _Cluster: https://docs.coiled.io/user_guide/api.html#coiled.Cluster
