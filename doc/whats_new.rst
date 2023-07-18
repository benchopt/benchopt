.. _whats_new:

What's new
==========

.. currentmodule:: benchopt

.. _changes_1_5:

Version 1.5 (dev)
-----------------

API
~~~

- ``Solver.support_sparse`` attribute is deprecated in favor of the use of
``Solver.skip``, by `Mathurin Massias`_ (:gh:`614`).

- ``stopping_strategy`` attribute is replaced by ``sampling_strategy`` to clarify
  the concept, by `Mathurin Massias`_ (:gh:`585`).

- Add ``Solver.warm_up`` function for explicit warmup instructions, such as
  empty run for jitting. This function is called only once per solver.
  By `Pierre Ablin`_ (:gh:`602`).

.. _changes_1_4:

Version 1.4 - 03/07/2023
------------------------

CLI
~~~

- Add support for minute and hour unit suffix in timeout limit through the syntax
  ``--timeout 10m`` or ``--timeout 1h``.
  By `Mathurin Massias`_ (:gh:`535`).
- Remove deprecated ``-o/--objective-filter`` option in ``benchopt run``.
  By `Thomas Moreau`_ (:gh:`569`)


API
~~~

- The ``get_next`` method of :class:`~benchopt.BaseSolver` is no longer static.
  By `Badr Moufad`_ (:gh:`566`)

- Add :class:`~benchopt.stopping_criterion.SingleRunCriterion` to run a solver
  only once. This can be used for benchmarking methods where we are interested
  in objective value at convergence. By `Thomas Moreau`_ (:gh:`511`)

- Add :func:`~benchopt.BaseSolver.run_once` helper to easily warmup solvers
  with callback. By `Thomas Moreau`_ (:gh:`511`)

- Add :func:`~benchopt.BaseSolver.pre_run_hook` hook to ignore cost that cannot
  be cached globally for a solver. By `Thomas Moreau`_ (:gh:`525`)

- Remove deprecated ``Objective.to_dict``, ``safe_import_context.import_from``.
  Force implementation of :method:`benchopt.Objective.get_one_solution`.
  By `Thomas Moreau`_ (:gh:`569`)

PLOT
~~~~

- Add a tooltip beside to show description of objective. Description is provided as docstring of
  the :class:`~benchopt.BaseObjective` class. By `Badr Moufad`_ (:gh:`556`)

- Show solver description when hovering over solvers. Description is provided as docstring of
  the :class:`~benchopt.BaseSolver` class. By `Badr Moufad`_ (:gh:`543`)

- Enable visualizing the objective as function of ``stopping_criterion``: time,
  iteration, or tolerance. By `Badr Moufad`_ (:gh:`479`)

FIX
~~~

- Do not fail and raise a warning when ``safe_import_context`` is not named
  ``import_ctx``. By `Mathurin Massias`_ (:gh:`524`)


.. _changes_1_3_1:

Version 1.3.1 - 01/12/2022
--------------------------

Bug fix release

FIX
~~~

- Typo in README and doc

- Barchart solver color to be the same as the other plots.

- Warning for deprecation not using the right class

- Plot quantile incorrect display

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

- Now the result data are saved in the Parquet format. The use of CSV files is deprecated.
  By `Melvine Nargeot`_ (:gh:`433`).

- Change the default number of repetitions to ``1``.
  By `Benoît Malézieux`_ (:gh:`457`).

API
~~~

- Allow changing tracked metric in ``StoppingCriterion``.
  By `Amélie Vernay`_ and `Thomas Moreau`_ (:gh:`461`).

- Add latest git tag via ``benchmark-git-tag`` key in :func:`benchopt.utils.sys_info.get_sys_info`.
  By `Mathurin Massias`_ (:gh:`421`).

- Deprecate ``Objective.to_dict`` in favor of :func:`~benchopt.BaseObjective.get_objective`.
  By `Mathurin Massias`_ (:gh:`489`).

- Deprecate ``import_from`` in favor of a ``benchmark_utils`` module dynamically installed
  when running a benchmark. By `Mathurin Massias`_ and `Thomas Moreau`_ (:gh:`472`).

- Allow specifying channels for conda requirements with syntax ``chan:deps``.
  By `Thomas Moreau`_ (:gh:`483`).

- Allow for template ``Solver`` and ``Dataset`` in ``datasets``/ ``solvers`` directory.
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
  which measures progress relative to the best attained value instead of
  the previous one, by `Thomas Moreau`_ (:gh:`176`)

- Now all values returned by ``Objective.compute`` are included in reports,
  by `Thomas Moreau`_ and `Alexandre Gramfort`_ (:gh:`200`).

- New ``--n-jobs, -j`` option to run the benchmark in parallel with
  ``joblib``, by `Thomas Moreau`_ (:gh:`265`).

API
~~~

- When returning a dictionary, ``Objective.compute`` should at least include
  ``value`` key instead of ``objective_value``, by `Thomas Moreau`_ and
  `Alexandre Gramfort`_ (:gh:`200`).

- ``stop_strategy`` attribute is replaced by ``stopping_strategy`` to harmonize
  with ``stopping_criterion``, by `Benoît Malézieux`_ (:gh:`274`).

- Add ``import_from`` method in ``safe_import_context`` to allow importing common
  files and packages without installation from `BENCHMARK_DIR/utils`,
  by `Thomas Moreau`_ (:gh:`286`).

- Add ``X_density`` argument to ``datasets.make_correlated_data`` to simulate
  sparse design matrices, by `Mathurin Massias`_ (:gh:`289`).

- ``Dataset.get_data`` should now return a dictionary and not a tuple. A point for
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

- Support Plotly for plotting functions, by `Thomas Moreau`_,
  `Tanguy Lefort`_ and `Joseph Salmon`_ (:gh:`110`, :gh:`111`, :gh:`112`).

- Change envrionment variable for config from ``BENCHO_*`` to ``BENCHOPT_*``,
  by `Thomas Moreau`_ (:gh:`128`).

- Add autocompletion support in the ``benchopt`` command,
  by `Alexandre Gramfort`_, `Tanguy Lefort`_ and `Thomas Moreau`_
  (:gh:`133`, :gh:`135`).

- Move most CI to GitHub action, with auto-release on PyPi,
  by `Thomas Moreau`_ (:gh:`150`, :gh:`154`).

- Remove ``BENCHOPT_ALLOW_INSTALL`` and always install to requested env as
  the user now must request explicitly the install,
  by `Thomas Moreau`_ (:gh:`155`).

API
~~~

- ``Objective.compute`` can now return a dictionary with multiple outputs to
  monitor several metrics at once, by `Thomas Moreau`_ (:gh:`84`).

- ``Solver.skip`` can now be used to skip objectives that are incompatible
  for the Solver, by `Thomas Moreau`_ (:gh:`113`).

- ``Solver`` can now use ``stop_strategy='callback'`` to allow for
  single call curve construction, by `Tanguy Lefort`_ and `Thomas Moreau`_
  (:gh:`137`).

- Add ``StoppingCriterion`` to reliably and flexibly assess a solver convergence (cvg).
  For now, only ``SufficientDescentCriterion`` is implemented but better
  API to set criterion per benchmark should be implemented in a future release,
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

- Add ``benchopt clean`` command to remove cached files and output files locally,
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

- Improve how-to narrative documentation, by `Alexandre Gramfort`_ (:gh:`93`).

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
