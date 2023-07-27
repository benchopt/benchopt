.. _get_started:

Get started
===========

Installation
------------

The recommended way to use benchopt is within a conda environment to fully benefit from all its features.
Hence, start by creating a dedicated conda environment and then activate it.

.. prompt:: bash $

    conda create -n benchopt python
    conda activate benchopt

Benchopt is available on PyPi. You can get the **stable version** via ``pip`` by running the following command

.. prompt:: bash $

    pip install -U benchopt

Eager to try out the **development version**? You can run instead

.. prompt:: bash $

    pip install -U -i https://test.pypi.org/simple/benchopt

.. attention::

   The **development version** is a work in progress and hence might contain incomplete features.
   A typical user is advised to use the **stable version** instead.

Once benchopt is installed, you get access to the :ref:`Command Line Interface (CLI) <cli_ref>`,
which enables a simple manipulation of benchmarks from the terminal.


Run an existing benchmark
-------------------------

Let's get the first steps with benchopt by comparing some solvers of the
`Lasso problem <https://en.wikipedia.org/wiki/Lasso_(statistics)>`_ on a
`Leukemia dataset <https://www.science.org/doi/10.1126/science.286.5439.531>`_.

Benchopt community maintains :ref:`several optimization benchmarks <available_benchmarks>`
and thrives to make them accessible and up to date, so as for the Lasso problem.

Start by cloning the Lasso benchmark repository and then ``cd`` to it.

.. prompt:: bash $

    git clone https://github.com/benchopt/benchmark_lasso.git
    cd benchmark_lasso

Then use benchopt to install the requirements for the solvers `skglm <https://contrib.scikit-learn.org/skglm/>`_ and
`scikit-learn <https://scikit-learn.org/stable/>`_, and the dataset Leukemia.

.. prompt:: bash $

    benchopt install -s skglm -s sklearn -d leukemia

Finally, run the benchmark

.. prompt:: bash $

    benchopt run . -s skglm -s sklearn -d leukemia

.. note::

    To explore all benchopt CLI features, refer to :ref:`cli_ref`
    or run ``benchopt --help`` or ``benchopt COMMAND_NAME --help``.

When the run is finished, benchopt automatically opens a window in you default browser and renders the results as a dashboard.

.. figure:: ./_static/results-get-started-lasso.png
   :align: center
   :alt: Dashboard of the Lasso benchmark results

   Desults dashboard

The dashboard displays benchmark-defined metrics tracked throughout the benchmark run such as the evolution of the objective value over time.


What's next?
------------

After this glimpse of benchopt, you can explore more advanced topics
such as writing your own benchmark, modifying an existing one, and customizing the benchmark's run options.
