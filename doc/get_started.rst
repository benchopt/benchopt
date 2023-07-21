.. _get_started:

Get started
===========

Installation
------------

The recommended way to use benchopt is within a conda environment to fully-benefit from all its features.
Hence, start with creating a dedicated conda environment. 

.. code-block:: bash

    # create conda environment with name benchopt
    conda create -n benchopt python

    # activate the environment
    conda activate benchopt

Benchopt is available on PyPi. You can get the **stable version** via ``pip`` by running the following command

.. code-block:: bash

    pip install -U benchopt

Eager to try out the **development version**? you can run instead

.. code-block:: bash

    pip install -U -i https://test.pypi.org/simple/benchopt

.. attention::

   The **development version** is a work in progress and hence might contain incomplete features.
   A typical user is advised to use the **stable version** instead.

With benchopt being installed, you get access to the :ref:`Command Line Interface (CLI) <cli_ref>`,
which enables simple and easy manipulation of benchmarks just from the terminal.


Run an existing benchmark
-------------------------

Let's get the first steps with benchopt by comparing some solvers of
`Lasso problem <https://en.wikipedia.org/wiki/Lasso_(statistics)>`_ on a
`Leukemia dataset <https://www.science.org/doi/10.1126/science.286.5439.531>`_.

Benchopt community maintains :ref:`several optimization benchmarks <available_benchmarks>`
and thrives at making them accessible and up to date, so as for the Lasso problem.

Start by cloning the Lasso benchmark repository

.. code-block:: bash

    # clone the repository
    git clone https://github.com/benchopt/benchmark_lasso.git

    # change directory
    cd benchmark_lasso

Then install automatically the benchmark requirements.
Here we compare `skglm <https://contrib.scikit-learn.org/skglm/>`_ and
`scikit-learn <https://scikit-learn.org/stable/>`_ solvers

.. code-block:: bash

    # install solvers
    benchopt install -s skglm -s sklearn

    # install dataset
    benchopt install -d leukemia

Finally, run the benchmark

.. code-block:: bash

    benchopt run . -s skglm -s sklearn -d leukemia

.. note::

    To explore all benchopt CLI features, refer to :ref:`cli_ref`
    or run ``benchopt --help`` or ``benchopt COMMAND_NAME --help``.

After completion, benchopt will automatically open a window in you default browser
and render the results of the benchmark as dashboard.

.. figure:: ./_static/results-get-started-lasso.png
   :align: center
   :alt: Dashboard of the Lasso benchmark results

   Dashboard of the benchmark results

The dashboard exhibits user-defined metrics tracked throughout the benchmark run
such as the evolution of the objective over time.


What's next?
------------

Now that you have a glimpse on benchopt, you can explore more advanced topics
such writing your own benchmark, modifying exiting ones, and customizing the benchmark's run. 
