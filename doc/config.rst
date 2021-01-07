.. _config_doc:

BenchOpt configuration
======================

BenchOpt can be configured using setting files. These files can either be created directly or generated and modified using ``benchopt config``.

There are two configuration levels. The first level is the global config for the ``benchopt`` client. It contains the system specific tweaks, the user info such as the *<GitHub token>* and the output levels. The second level is the configuration of the benchmarks. Each benchmark can have its own config for the kind of plots it displays by default and other display tweaks.

To get the BenchOpt global config file used by the ``benchopt`` command, you can run ``benchopt config``. Using the option ``--benchmark,-b <benchmark>`` allows to display the config file for a specific benchmark. See :ref:`config_file` for more details on how the config file path is resolved.

The structure of the files follows the Microsoft Windows INI files structure and is described in :ref:`config_structure`. The available settings are listed in :ref:`config_settings`.

The value of each setting can be accessed with the CLI using ``benchopt config [-b <benchmark>] get <name>``. Similarly, the setting value can be set using ``benchopt config [-b <benchmark>] set <name> <value>``.

.. _config_file:

Config File Location
--------------------

For global config file, the resolution order is the following:

1. The environment variable ``BENCHOPT_CONFIG`` is set to an existing file,
2. A file ``benchopt.ini`` in the current directory,
3. The default file is ``$HOME/.config/benchopt.ini``.

For benchmark config files, they are usually located in the benchmark folder with name ``benchopt.ini``. If it does not exists, the default is to use the global config file.

.. _config_structure:

Config File Structure
---------------------

The config files for benchOpt follow the Microsoft Windows INI files structure. The global setting are grouped in a ``[benchopt]`` section:

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
        histogram
        objective_curve


.. _config_settings:

Config Settings
---------------

This section lists the available settings.


Global settings
~~~~~~~~~~~~~~~

.. autodata:: benchopt.config.DEFAULT_GLOBAL_CONFIG



Benchmark settings
~~~~~~~~~~~~~~~~~~~

.. autodata:: benchopt.config.DEFAULT_BENCHMARK_CONFIG

