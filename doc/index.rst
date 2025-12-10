
``Benchopt``
=============

*—Making your ML and optimization benchmarks simple and open—*


|Python 3.10+| |PyPI version| |License|

Benchopt is a benchmarking suite tailored for machine learning workflows.
It is built for simplicity, transparency, and reproducibility.
It is implemented in Python but can run algorithms written in many programming languages.

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

   .. tab-item:: Bilevel Optimization

      A benchmark comparing various algorithms to solve bilevel optimization problems.

      .. prompt:: bash $

         git clone https://github.com/benchopt/benchmark_bilevel.git
         benchopt run benchmark_bilevel

      which will produce an interactive HTML report to visualize the results.

      .. raw:: html

         <iframe class="benchmark_result"
               src="https://benchopt.github.io/results/benchmark_bilevel_benchmark_bilevel_ijcnn1.html"
            frameBorder='0' style="position: relative; width: 100%;">
         </iframe>

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
with benchopt, from deep learning optimization to more classical machine learning tasks.
There are already many :ref:`available_benchmarks` that have been created using benchopt.
Learn how to run them and how to construct your own with the following pages!

.. grid:: 2
    :gutter: 1

    .. grid-item-card::
        :link: get_started
        :link-type: ref

        :octicon:`rocket` **Get started**
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        Install benchopt and run your first benchmark

    .. grid-item-card::
        :link: benchmark_workflow
        :link-type: ref

        :octicon:`tools` **Benchmark workflow**
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        Write a benchmark from scratch, run it, visualize it, and publish it

    .. grid-item-card::
        :link: tutorials
        :link-type: ref

        :octicon:`mortar-board` **Tutorials**
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        Gallery of use-cases crafted by the benchopt community

    .. grid-item-card::
        :link: user_guide
        :link-type: ref

        :octicon:`book` **User guide**
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        Full documentation of benchopt API and CLI


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
   tutorials/index
   user_guide/index

   available_benchmarks
   contrib
   whats_new
