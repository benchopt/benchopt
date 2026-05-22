
``Benchopt``
=============

*—A framework for reproducible, comparable benchmarks—*


|Python 3.10+| |PyPI version| |License|

Benchopt is a benchmarking framework for **machine learning and optimization**.
You bring **datasets**, **metrics**, and the **methods** to compare —
Benchopt provides the loop that connects them and runs reproducible comparisons
at scale. Out of the box:

* **Scale experiments:** loop over grid of parameters, run in parallel locally or on HPC clusters, with native SLURM support.
* **Save time:** cache results to avoid recomputing unchanged runs.
* **Trust comparisons:** control randomness with seeds and stable protocols.
* **Integrate broadly:** use implementations from Python, R, Julia, or binaries.
* **Share outcomes:** merge and publish results from multiple runs, with easy interactive visualization.
* **Maintain and Extend:** modular design to easily add new datasets, solvers, and metrics, and CI tools to test them.

Learn how to construct and run a benchmark with the following pages!

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

.. tip::
   **Want to create a new benchmark with benchopt?** Use our templates to get started:
   `ML benchmarks <https://github.com/benchopt/template_benchmark_ml>`_ |
   `Optimization benchmarks <https://github.com/benchopt/template_benchmark>`_


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
