.. _whats_new:

What's new
==========

.. currentmodule:: benchopt

.. _changes_1_1:

Version 1.1 - 22-04-2021
------------------------

Changelog
~~~~~~~~~

- New plotting functions with different optimality criteria,
  by `Nidham Gazagnadou`_ (:gh:`96`).

- Support plotly for plotting functions, by `Thomas Moreau`_,
  `Tanguy Lefort`_ and `Joseph Salmon`_ (:gh:`110`, :gh:`111`, :gh:`112`).

- Change envrionment variable for config from `BENCHO_*` to `BENCHOPT_*`,
  by `Thomas Moreau`_ (:gh:`128`).

- Add autocompletion support in the `benchopt` command,
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
  monitor several metrics at once, by `Thomas Moreau`_ (gh:`84`).

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

BUG
~~~

- Throw a warning when BenchOpt version in conda env does not match the one of
  calling ``benchopt``, by `Thomas Moreau`_ (:gh:`83`).

- Fix Lapack issue with R code, by `Tanguy Lefort`_ (:gh:`97`).


DOC
~~~

- Improve how-to narative documentation, by `Alexandre Gramfort`_ (:gh:`93`).

- Add what's new page, by `Alexandre Gramfort`_ (:gh:`114`).

- Add documentation on how to publish results, by `Alexandre Gramfort`_ (:gh:`118`).


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
