.. _install_benchmark:

Install a benchmark
======================

In order to make it easy to run a new benchmark, benchopt provides an interface
to specify and install requirements for the various components of the benchmarks.

- By default, calling ``benchopt install .`` will install the requirements for the
  benchmark, including all solvers and datasets, using the ``conda-forge`` channel.

- The minimum requirements to run the benchmark are specified in
  ``objective.py``. They can be installed using the command
  ``benchopt install --minimal``.

- The requirements that are specific to each ``Dataset/Solver`` can be
  specified in each class, and they can be installed individually by selecting
  the proper component using ``benchopt install -d dataset1 -s solver1``.

- Finally, it is possible to use this command to download necessary files for
  datasets, prior to running the benchmark. This can be done using the
  ``--download`` option. This is particularly useful when running the benchmark
  on a remote server where internet access is not available during the benchmark
  execution.


.. _specify_requirements:

Specifying requirements
-----------------------

To specify how dependencies should be installed, you can use the ``install_cmd`` class attribute.
This attribute accepts two possible values:

  1. ``conda`` (default): Dependencies will be installed using Conda. In this case, you should
  specify the required dependencies in the ``requirements`` class attribute. Note that
  dependencies to install with ``pip`` are also specified with this option.

  2. ``shell``: This option allows you to provide a custom shell script for installing dependencies.
  When using this value, you need to set the ``install_script`` class attribute to the path of your shell script.
  Benchopt will execute this script in the shell and pass the Conda environment directory as an argument.


By properly setting these attributes, you ensure that all dependencies are installed
correctly. This will help users to run your benchmarks without any issues.

Examples:

.. code-block:: python

  requirements = ['pkg']  # conda package `pkg`
  requirements = ['chan::pkg']  # package `pkg` in conda channel `chan`


One might also need to install pip packages. This can be done by using the
channel `pip` and the `conda` installer. The syntax is the following:

.. code-block:: python

  install_cmd = 'conda'  # optional
  requirements = ['pip::pkg']  # pip package `pkg`

