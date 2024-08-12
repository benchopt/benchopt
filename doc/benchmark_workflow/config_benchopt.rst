.. _config_benchopt:

Configure Benchopt
==================


Benchopt can be configured using setting files. These files can either be created directly or generated and modified using ``benchopt config``.

There are two configuration levels. The first level is the global config for the benchopt client. It contains the system-specific tweaks, the user info such as the *<GitHub token>*, and the output levels. The second level is the configuration of the benchmarks. Each benchmark can have its own config for the kind of plots it displays by default and other display tweaks.

To get the BenchOpt global config file used by the benchopt command, you can run ``benchopt config``. Using the option ``--benchmark,-b <benchmark>`` allows to display the config file for a specific benchmark. See :ref:`config_file` for more details on how the config file path is resolved.

The structure of the files follows the Yaml files structure and is described in :ref:`config_structure`. The available settings are listed in :ref:`config_settings`.

The value of each setting can be accessed with the CLI using ``benchopt config [-b <benchmark>] get <name>``. Similarly, the setting value can be set using ``benchopt config [-b <benchmark>] set <name> <value>``.

.. _config_file:

Config File Location
--------------------

For the global configuration file, the resolution order is the following:

1. The environment variable ``BENCHOPT_CONFIG`` is set to an existing file,
2. A file ``benchopt.yml`` in the current directory,
3. The default file is ``$HOME/.config/benchopt.yml``.

For benchmark configuration files, they are usually located in the benchmark folder, and named ``benchopt.yml``. If it does not exist, the default is to use the global config file.

.. _config_structure:

Config File Structure
---------------------

The config files for benchopt follow the YAML files structure:

.. code-block:: yml

    debug: true  # Activate or not debug logs. Default is false.
    conda_cmd: mamba  # Command to use to install packages. Default is conda.
    github_token: 0...0  # Token used to publish results on benchopt/results

For benchmark settings, they are grouped in a section with the same name as the benchmark. For a benchmark named ``benchmark_bench``, the config structure is:

.. code-block:: yml

    benchmark_bench:
        plots:
            - suboptimality_curve
            - bar_chart
            - objective_curve
        data_paths:
            imagenet: /path/to/imagenet

Note that specific benchmark config can also be set into the config file of the benchmark, located in the benchmark folder. The global config file is used as a fallback if the benchmark config file does not exist.


.. _config_settings:

Config Settings
---------------

This section lists the available settings.


**Global settings**

.. autodata:: benchopt.config.DEFAULT_GLOBAL_CONFIG



**Benchmark settings**

.. autodata:: benchopt.config.DEFAULT_BENCHMARK_CONFIG


.. _config_mamba:

Using ``mamba`` to install packages
-----------------------------------

When many packages need to be installed, ``conda`` can be slow or even fail to resolve the dependency graph. Using ``mamba`` can speed up this process and make it more reliable.

To use ``mamba`` instead of ``conda`` when installing benchmark requirements, it is necessary to have ``mamba`` installed in the ``base`` conda environment, *e.g.* using ``conda install -n base mamba``. Then, benchopt can be configured to use this command instead of ``conda`` by either configuring the CLI using ``benchopt config set conda_cmd mamba`` or setting the environment variable ``BENCHOPT_CONDA_CMD=mamba``.
