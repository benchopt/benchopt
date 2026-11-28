``Benchopt``
=============

**Compare machine learning and optimization methods side by side.**
*Same data, same metrics, every method.*

Benchopt runs each method on the same data, scores it with the same metrics,
and plots the results. Start from an existing benchmark and add your method in
one file, or turn the protocol of a paper into a benchmark that others can
rerun and extend. Your coding agent can do most of the work.

:ref:`See a comparison <featured_benchmarks>` · :ref:`Run your first benchmark <get_started>`

.. raw:: html

   <object class="benchopt-figure benchopt-add" data="_static/benchopt_add_method.svg"
           type="image/svg+xml"
           aria-label="Add your method to an existing benchmark: benchopt runs it with the same data and metrics as the other methods, and plots how it compares.">
   </object>


One benchmark, three uses
-------------------------

.. tab-set::
    :class: goal-tabs

    .. tab-item:: :octicon:`person` Compare my method
        :sync: research

        Pick the experimental protocol of a paper, turn it into a reproducible
        benchmark (typically with your coding agent), then add the missing
        baselines, your method, or the use cases you think matter. You get
        figures for your paper and results others can rerun.

        **Example:** the `simulated benchmark
        <https://github.com/soda-inria/crossing-the-validation-crisis/tree/main/simulated>`_
        behind the NeurIPS 2026 paper *Crossing the Validation Crisis*.

        **Start from a template:**
        `ML <https://github.com/benchopt/template_benchmark_ml>`_ |
        `optimization <https://github.com/benchopt/template_benchmark>`_

    .. tab-item:: :octicon:`people` Run a competition
        :sync: competition

        Evaluate the methods submitted by participants, with the same scoring
        for all. The test data and some methods can stay private, and the
        results feed a leaderboard.

        **Example:** the `neural-interfaces 2026 competition
        <https://github.com/neural-interfaces26/2026-competition>`_, run on
        Codabench.

        **Start from the** `Codabench template
        <https://github.com/benchopt/template_codabench>`_.

    .. tab-item:: :octicon:`organization` Maintain a reference benchmark
        :sync: reference

        Give a consolidated view of a field, across many test cases. The
        community adds datasets, metrics and methods, and the results are
        published on a live site.

        **Examples:** `L2-regularized logistic regression
        <https://github.com/benchopt/benchmark_logreg_l2>`_,
        `unsupervised domain adaptation
        <https://github.com/scikit-adaptation/skada-bench>`_.

        **Publish your results:** see :ref:`publish_benchmark`.


Explore benchopt
----------------

.. raw:: html

   <object class="benchopt-figure benchopt-overview" data="_static/benchopt_overview.svg"
           type="image/svg+xml"
           aria-label="Research, competitions and reference benchmarks all rely on one benchopt benchmark, which produces paper figures, reusable results, leaderboards and a live results site.">
   </object>
   <p class="overview-hint">Hover a use to see what it relies on and produces,
   click a tool or an arrow to open its documentation.</p>


Use benchopt
------------

Start small and grow when needed: run one of the :ref:`available_benchmarks`, add your method
as one file, write your own benchmark from a template, then scale it to a
cluster or open it to others.

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
