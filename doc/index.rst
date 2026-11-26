``Benchopt``
=============

**Standardized benchmarks for AI and optimization.**
*Same data, same metrics, every method.*


|Python 3.10+| |PyPI version| |License|

Benchopt turns an evaluation protocol into shared code. A benchmark fixes
**the data** (datasets) and **the evaluation** (an objective and its metrics),
and runs every **method** (called a *solver*) under exactly the same
conditions. Because the evaluation lives in one place, a new metric or a fixed
bug applies to all methods at once, and a single ``benchopt run`` updates the
whole comparison.

.. raw:: html

   <object class="benchopt-overview" data="_static/benchopt_overview.svg"
           type="image/svg+xml"
           aria-label="Research, competitions and reference benchmarks all rely on one benchopt benchmark, which produces paper figures, reusable results, leaderboards and a live results site.">
   </object>


One benchmark, three goals
--------------------------

The same benchmark serves very different goals. Hover a goal in the figure
above to see what it uses and what it produces.

.. grid:: 1 1 3 3
    :gutter: 2

    .. grid-item-card::

        :octicon:`person` **Research**
        ^^^
        Create a new method or answer a research question. Compare it to
        baselines without rewriting the evaluation, and get the figures for
        your paper.

        *Example:* the `simulated benchmark
        <https://github.com/soda-inria/crossing-the-validation-crisis/tree/main/simulated>`_
        behind the NeurIPS 2026 paper *Crossing the Validation Crisis*.
        +++
        Start from a template:
        `ML <https://github.com/benchopt/template_benchmark_ml>`_ |
        `optimization <https://github.com/benchopt/template_benchmark>`_

    .. grid-item-card::

        :octicon:`people` **Competition**
        ^^^
        Evaluate the methods submitted by participants, with the same scoring
        for all. The test data and some methods can stay private, and the
        results feed a leaderboard.

        *Example:* the `neural-interfaces 2026 competition
        <https://github.com/neural-interfaces26/2026-competition>`_, run on
        Codabench.
        +++
        Start from the `Codabench template
        <https://github.com/benchopt/template_codabench>`_

    .. grid-item-card::

        :octicon:`organization` **Reference benchmark**
        ^^^
        Give a consolidated view of a field, across many test cases. The
        community adds datasets, metrics and methods, and the results are
        published on a live site.

        *Examples:* `L2-regularized logistic regression
        <https://github.com/benchopt/benchmark_logreg_l2>`_,
        `unsupervised domain adaptation
        <https://github.com/scikit-adaptation/skada-bench>`_.
        +++
        See :ref:`publish_benchmark`


A toolbox for benchmark campaigns
---------------------------------

Benchopt runs every method on every dataset and every parameter, and takes
care of the rest:

* **Scale experiments:** run in parallel locally or on HPC clusters, with
  native SLURM support.
* **Save time:** cache results, checkpoint long runs, and reuse past results
  instead of recomputing them.
* **Trust comparisons:** control randomness with seeds, and check every
  component with ``benchopt test``.
* **Find bottlenecks:** profile solvers line by line with ``--profile``.
* **Integrate broadly:** write solvers in Python, R, Julia, or wrap binaries.
* **Share outcomes:** merge runs and publish interactive reports.
* **Work with your agent:** ``benchopt sync-skills`` teaches your coding agent
  how to write, run and debug a benchmark. See :ref:`agent_skills`.

Start small and grow when needed: run an existing benchmark, add your method
as one file, write your own benchmark from a template, then scale it to a
cluster or open it to others.


Learn benchopt
--------------

.. grid:: 2
    :gutter: 1

    .. grid-item-card::
        :link: get_started
        :link-type: ref

        :octicon:`rocket` **Get started**
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        Install benchopt, run an existing benchmark, and write your own
        with minimal working examples

    .. grid-item-card::
        :link: benchmark_workflow
        :link-type: ref

        :octicon:`tools` **Benchmark workflow**
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        Write an ML or optimization benchmark from scratch,
        run it, visualize it, and publish it

    .. grid-item-card::
        :link: user_guide
        :link-type: ref

        :octicon:`book` **User guide**
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        Full documentation of benchopt API and CLI

    .. grid-item-card::
        :link: general_examples
        :link-type: ref

        :octicon:`mortar-board` **Examples**
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        Gallery of use-cases crafted by the benchopt community


.. _faq:

.. Frequently Asked Questions (FAQ) subsection
.. include:: faq.rst

Example benchmarks
------------------

Reproducing an existing benchmark should be as easy as running the following commands:

.. tab-set::

   .. tab-item:: NanoGPT

      A benchmark comparing various optimizers on training ``NanoGPT`` models.

      .. prompt:: bash $

         git clone https://github.com/benchopt/benchmark_nanogpt.git
         benchopt run benchmark_nanogpt

      which will produce an interactive HTML report to visualize the results.

      .. raw:: html

         <iframe class="benchmark_result"
               src="https://benchopt.github.io/results/benchmark_nanogpt_benchmark_nanogpt_benchopt_run_2025-10-31_13h48m48.html"
            frameBorder='0' style="position: relative; width: 100%;">
         </iframe>

   .. tab-item:: Unsupervised Domain Adaptation

      A benchmark comparing various methods for unsupervised domain adaptation.

      .. prompt:: bash $

         git clone https://github.com/scikit-adaptation/skada-bench.git
         benchopt run skada-bench --config configs/Simulated.yml --no-plot

      which will produce a parquet file with the results that can be visualized
      using instruction on the ``README.md`` of the https://github.com/scikit-adaptation/skada-bench.

   .. tab-item:: Minimal benchmark

      A minimal benchmark comparing various solvers on a toy problem.

      .. prompt:: bash $

         benchopt run examples/minimal_benchmark

      which will produce an interactive HTML report to visualize the results.

      .. raw:: html

         <iframe class="benchmark_result"
               src="auto_examples/html_results/sphx_glr_run_minimal_benchmark_002.html"
            frameBorder='0' style="position: relative; width: 100%;">
         </iframe>


These different tabs illustrate the diversity of benchmarks that can be built
with benchopt, from deep learning optimization to more classical machine
learning tasks.

There are already many :ref:`available_benchmarks` that have been created using benchopt.


Join the community
------------------

Join benchopt `discord server <https://discord.gg/EA2HGQb7nv>`_ and get in touch with the community!

Feel free to drop a message to get help with running/constructing benchmarks
or (why not) discuss new features to be added and future development directions that benchopt should take.


Citing Benchopt
---------------

Benchopt is a continuous effort to make reproducible and transparent ML and optimization benchmarks.
Join this endeavor! If you use benchopt in a scientific publication, please cite

.. code-block:: bibtex

   @inproceedings{benchopt,
      author    = {Moreau, Thomas and Massias, Mathurin and Gramfort, Alexandre
                   and Ablin, Pierre and Bannier, Pierre-Antoine
                   and Charlier, Benjamin and Dagréou, Mathieu and Dupré la Tour, Tom
                   and Durif, Ghislain and F. Dantas, Cassio and Klopfenstein, Quentin
                   and Larsson, Johan and Lai, En and Lefort, Tanguy
                   and Malézieux, Benoit and Moufad, Badr and T. Nguyen, Binh and Rakotomamonjy,
                   Alain and Ramzi, Zaccharie and Salmon, Joseph and Vaiter, Samuel},
      title     = {Benchopt: Reproducible, efficient and collaborative optimization benchmarks},
      year      = {2022},
      booktitle = {NeurIPS},
      url       = {https://arxiv.org/abs/2206.13424}
   }


.. |Python 3.10+| image:: https://img.shields.io/badge/python-3.10%2B-blue
   :target: https://www.python.org/downloads/release/python-3100/
.. |License| image:: https://img.shields.io/badge/License-BSD_3--Clause-blue.svg
   :target: https://github.com/benchopt/benchopt/blob/main/LICENSE
.. |PyPI version| image:: https://badge.fury.io/py/benchopt.svg
   :target: https://pypi.org/project/benchopt/


.. it mandatory to keep the toctree here although it doesn't show up in the page
.. when adding/modifying pages, don't forget to update the toctree

.. toctree::
   :maxdepth: 2
   :hidden:
   :includehidden:

   get_started
   benchmark_workflow/index
   user_guide/index
   auto_examples/index
   available_benchmarks
   contrib
   whats_new
