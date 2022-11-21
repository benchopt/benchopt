.. _whats_new:

What's new
==========

.. currentmodule:: benchopt

.. _changes_1_3:

Version 1.3 - 21/11/2022
------------------------

CLI
~~~

- Add support for custom parameters in CLI for objectives, datasets, and
  solvers, through the syntax ``-s solver_name[parameter=value]``. See the `CLI
  documentation <https://benchopt.github.io/cli.html>`_ for more details on the
  syntax. By `Tom Dupré la Tour`_ (:gh:`362`).

- Add ``--slurm`` option in ``benchopt run`` to allow running the benchmark on
  a SLURM cluster. See the :ref:`slurm_run` for more details on the config.
  By `Thomas Moreau`_ (:gh:`407`)

- Add ``benchopt archive`` to create a ``tar.gz`` archive with the benchmark's
  files for sharing with others or as supplementary materials for papers.
  By `Thomas Moreau`_ (:gh:`408`).

- Now the result data are saved in the Parquet format. The use of CSV file is deprecated.
  By `Melvine Nargeot`_ (:gh:`433`).

- Change default number of repetitions to ``1``.
  By `Benoît Malézieux`_ (:gh:`457`).

API
~~~

- Allow to change tracked metric in `StoppingCriterion`.
  By `Amélie Vernay`_ and `Thomas Moreau`_ (:gh:`461`).

- Add latest git tag via ``benchmark-git-tag`` key in :func:`benchopt.utils.sys_info.get_sys_info`.
  By `Mathurin Massias`_ (:gh:`421`).

- Deprecate ``Objective.to_dict`` in favor of :func:`~benchopt.BaseObjective.get_objective`.
  By `Mathurin Massias`_ (:gh:`489`).

- Deprecate `import_from` in favor of a `benchmark_utils` module dynamically installed
  when running a benchmark. By `Mathurin Massias`_ and `Thomas Moreau`_ (:gh:`472`).

- Allow to specify channels for conda requirements with synthax `chan:deps`.
  By `Thomas Moreau`_ (:gh:`483`).

- Allow for template `Solver` and `Dataset` in `datasets/solvers` directory.
  By `Thomas Moreau`_ (:gh:`473`).

.. _changes_1_2:

Version 1.2 - 06/05/2022
------------------------

Changelog
~~~~~~~~~

- New ``benchopt info`` command to display information about solvers and datasets
  of a benchmark, by `Ghislain Durif`_ (:gh:`140`).

- New ``--profile`` option to the ``run`` command in order to profile
  with the line-profiler package all functions decorated with
  :func:`benchopt.utils.profile`, by `Alexandre Gramfort`_ (:gh:`186`).

- Replace ``SufficientDescentCriterion`` by ``SufficientProgressCriterion``,
  which measures progress relatively to the best attained value instead of
  the previous one, by `Thomas Moreau`_ (:gh:`176`)

- Now all values returned by ``Objective.compute`` are included in reports,
  by `Thomas Moreau`_ and `Alexandre Gramfort`_ (:gh:`200`).

- New ``--n-jobs, -j`` option to run the benchmark in parallel with
  ``joblib``, by `Thomas Moreau`_ (:gh:`265`).

API
~~~

- When returning a dict, ``Objective.compute`` should at least include
  ``value`` key instead of ``objective_value``, by `Thomas Moreau`_ and
  `Alexandre Gramfort`_ (:gh:`200`).

- 'stop_strategy' attribute is replaced by 'stopping_strategy' to harmonize
  with 'stopping_criterion', by `Benoît Malézieux`_ (:gh:`274`).

- Add ``import_from`` method in ``safe_import_context`` to allow importing common
  files and packages without install from `BENCHMARK_DIR/utils`,
  by `Thomas Moreau`_ (:gh:`286`).

- Add ``X_density`` argument to ``datasets.make_correlated_data`` to simulate
  sparse design matrices, by `Mathurin Massias`_ (:gh:`289`).

- ``Dataset.get_data`` should now return a dict and not a tuple. A point for
  testing  should be returned by a dedicated method
  ``Objective.get_one_solution``, by `Thomas Moreau`_ (:gh:`345`).

CLI
~~~

- Replace ``-p`` flag by ``-o`` for Objective, by `Mathurin Massias`_ (:gh:`281`).

- Add ``--config`` option to support passing argument with a ``yaml``
  config file, by `Mathurin Massias`_ (:gh:`325`).

.. _changes_1_1:

Version 1.1 - 22-04-2021
------------------------

Changelog
~~~~~~~~~

- New plotting functions with different optimality criteria,
  by `Nidham Gazagnadou`_ (:gh:`96`).

- Support plotly for plotting functions, by `Thomas Moreau`_,
  `Tanguy Lefort`_ and `Joseph Salmon`_ (:gh:`110`, :gh:`111`, :gh:`112`).

- Change envrionment variable for config from ``BENCHO_*`` to ``BENCHOPT_*``,
  by `Thomas Moreau`_ (:gh:`128`).

- Add autocompletion support in the ``benchopt`` command,
  by `Alexandre Gramfort`_, `Tanguy Lefort`_ and `Thomas Moreau`_
  (:gh:`133`, :gh:`135`).

- Move most CI to github action, with auto-release on pypi,
  by `Thomas Moreau`_ (:gh:`150`, :gh:`154`).

- Remove ``BENCHOPT_ALLOW_INSTALL`` and always install to requested env as
  user now must request explicitely the install,
  by `Thomas Moreau`_ (:gh:`155`).

API
~~~

- ``Objective.compute`` can now return a dictionary with multiple outputs to
  monitor several metrics at once, by `Thomas Moreau`_ (:gh:`84`).

- ``Solver.skip`` can now be used to skip objectives that are incompatible
  for the Solver, by `Thomas Moreau`_ (:gh:`113`).

- ``Solver`` can now use ``stop_strategy = 'callback'`` to allow for
  single call curve construction, by `Tanguy Lefort`_ and `Thomas Moreau`_
  (:gh:`137`).

- Add ``StoppingCriterion`` to reliably and flexibly assess a solver cvg.
  For now, only ``SufficientDescentCriterion`` is implemented but better
  API to set criterion per benchmark should be implemented in future release,
  by `Thomas Moreau`_ (:gh:`151`)

CLI
~~~

- Add ``--version`` option for ``benchopt``, by `Thomas Moreau`_ (:gh:`83`).

- Add ``--pdb`` option for ``benchopt run`` to open debugger on error and help
  benchmark debugging, by `Thomas Moreau`_ (:gh:`86`).

- Change default run to local mode. Can call a run in a dedicated env with
  option ``--env`` or ``--env-name ENV_NAME`` to specify the env,
  by `Thomas Moreau`_ (:gh:`94`).

- Add ``benchopt publish`` command to push benchmark results to GitHub,
  by `Thomas Moreau`_ (:gh:`110`).

- Add ``benchopt clean`` command to remove cached file and output files locally,
  by `Thomas Moreau`_ (:gh:`128`).

- Add ``benchopt config`` command to allow easy configuration of ``benchopt``
  using the CLI, by `Thomas Moreau`_ (:gh:`128`).

- Add ``benchopt install`` command to install benchmark requirements
  (not done in ``benchopt run`` anymore) by `Ghislain Durif`_ (:gh:`135`).

- Add ``benchopt info`` command to print information about a benchmark
  (including solvers, datasets, dependencies, etc.)
  by `Ghislain Durif`_ (:gh:`140`).


BUG
~~~

- Throw a warning when benchopt version in conda env does not match the one of
  calling ``benchopt``, by `Thomas Moreau`_ (:gh:`83`).

- Fix Lapack issue with R code, by `Tanguy Lefort`_ (:gh:`97`).


DOC
~~~

- Improve how-to narative documentation, by `Alexandre Gramfort`_ (:gh:`93`).

- Add what's new page, by `Alexandre Gramfort`_ (:gh:`114`).

- Add documentation on how to publish results, by `Alexandre Gramfort`_ (:gh:`118`).

The committer list for this release is the following:

  * `Alexandre Gramfort`_
  * `Benoît Malézieux`_
  * `Ghislain Durif`_
  * `Joseph Salmon`_
  * `Mathurin Massias`_
  * `Nidham Gazagnadou`_
  * `Tanguy Lefort`_
  * `Thomas Moreau`_
  * `Tom Dupré la Tour`_

.. _changes_1_0:

Version 1.0 - 2020-09-25
------------------------

Release highlights
~~~~~~~~~~~~~~~~~~

- Provide a command line interface for benchmarking optimisation algorithm
  implementations:

  - ``benchopt run`` to run the benchmarks
  - ``benchopt plot`` to display the results
  - ``benchopt test`` to test that a benchmark folder is correctly structured.

The committer list for this release is the following:

  * `Alexandre Gramfort`_
  * `Joseph Salmon`_
  * `Mathurin Massias`_
  * `Thomas Moreau`_
  * `Tom Dupré la Tour`_

.. include:: names.inc
