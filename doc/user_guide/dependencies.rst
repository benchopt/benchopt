.. _managing_dependencies:

Managing dependencies
======================

Benchopt uses conda environments to isolate each benchmark's dependencies.
This page explains how to declare what each component needs and how to
control the Python version of the environment.

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


.. _specify_python_version:

Specifying a Python version
---------------------------

When benchopt creates a conda environment, it uses Python 3.12 by default.
If a benchmark requires a specific Python version, it can be declared via
the ``python_version`` class attribute on the ``Objective``.
Both an exact minor version and a PEP-440 specifier are accepted:

.. code-block:: python

    class Objective(BaseObjective):
        name = "my-benchmark"
        python_version = "3.11"    # exact: conda env will use Python 3.11.x
        # python_version = ">=3.11"  # specifier: any Python >= 3.11 is accepted
        ...

When running ``benchopt install --env-name myenv``, benchopt will:

- **Create** the conda env with the requested Python version if it does not
  exist yet. An exact version (e.g. ``"3.11"``) pins the minor version;
  a specifier (e.g. ``">=3.11"``) lets conda pick the newest compatible
  release.
- **Warn** if the env already exists but its Python version does not satisfy
  the constraint declared in the objective, so that users can recreate the
  env with ``--recreate`` if needed.

If ``python_version`` is not set, the default version (3.12) is used.
