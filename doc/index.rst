Benchopt 
========

*—Making your optimization benchmarks simple and open—*


|Test Status| |Python 3.6+| |codecov|

``Benchopt`` is a benchmarking suite for optimization algorithms.
It is built for simplicity, transparency, and reproducibility.
It is implemented in Python but can run algorithms written in **many programming languages**.

.. grid:: 2
    :gutter: 1

    .. grid-item-card::
        :link: contrib_doc
        :link-type: ref

        :octicon:`rocket` **Get started**
        ^^^
        Install ``benchopt`` and run your first benchmark

    .. grid-item-card::
        :link: contrib_doc
        :link-type: ref

        :octicon:`tools` **Build a benchmark**
        ^^^
        Write a benchmark from scratch, run it and visualize it


    .. grid-item-card::
        :link: contrib_doc
        :link-type: ref

        :octicon:`book` **User Guide**
        ^^^
        Full documentation of ``benchopt`` API and CLI


    .. grid-item-card::
        :link: contrib_doc
        :link-type: ref

        :octicon:`mortar-board` **Tutorials**
        ^^^
        A gallery of use-cases crafted by ``benchopt`` community


Get in touch with the community
-------------------------------

Join ``benchopt`` `discord server <https://discord.gg/EA2HGQb7nv>`_ and get in touch with the community!
Feel free to drop us a message to get help with running/constructing benchmarks 
or (why not) discuss new features to be added and future development directions that ``benchopt`` should take.


Citing Benchopt
---------------

``Benchopt`` is a continuous effort to make reproducible and transparent optimization benchmarks.
Join us in this endeavor! If you use ``benchopt`` in a scientific publication, please cite

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


.. |Test Status| image:: https://github.com/benchopt/benchopt/actions/workflows/test.yml/badge.svg
   :target: https://github.com/benchopt/benchopt/actions/workflows/test.yml
.. |Python 3.6+| image:: https://img.shields.io/badge/python-3.6%2B-blue
   :target: https://www.python.org/downloads/release/python-360/
.. |codecov| image:: https://codecov.io/gh/benchopt/benchopt/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/benchopt/benchopt



Explore
-------

.. toctree::
    :maxdepth: 1

    user_guide/index.rst