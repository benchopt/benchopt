
``Benchopt``
=============

*—Making your optimization benchmarks simple and open—*


|Python 3.6+| |PyPI version| |License|

Benchopt is a benchmarking suite for optimization algorithms.
It is built for simplicity, transparency, and reproducibility.
It is implemented in Python but can run algorithms written in many programming languages.

Reproducing an existing benchmark should be as easy as running

.. prompt:: bash $
   
   benchopt run . --config ./example_config.yml

.. figure:: https://benchopt.github.io/_images/sphx_glr_plot_run_benchmark_001.png
   :align: center
   :width: 70 %

There are already many :ref:`available_benchmarks` that have been created using benchopt.
Learn how to run them and how to construct your own with the following pages!

.. grid:: 1
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

Benchopt is a continuous effort to make reproducible and transparent optimization benchmarks.
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


.. |Python 3.6+| image:: https://img.shields.io/badge/python-3.6%2B-blue
   :target: https://www.python.org/downloads/release/python-360/
.. |License| image:: https://img.shields.io/badge/License-BSD_3--Clause-blue.svg
   :target: https://github.com/benchopt/benchopt/blob/main/LICENSE
.. |PyPI version| image:: https://badge.fury.io/py/benchopt.svg
   :target: https://pypi.org/project/benchopt/


.. it mandatory to keep the toctree here although it doesn't show up in the page
.. when adding/modifying pages, don't forget to update the toctree

.. toctree::
   :maxdepth: 1
   :hidden:
   :includehidden:

   get_started
   benchmark_workflow/index
   user_guide/index

   available_benchmarks
   contrib
   whats_new
