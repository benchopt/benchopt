Benchopt supports different types of solvers:

- :ref:`python_solvers`
- :ref:`r_solvers`
- :ref:`julia_solvers`
- :ref:`source_solvers`

.. _python_solvers:

Python solver
~~~~~~~~~~~~~

The simplest solvers to use are solvers using `Python <https://www.python.org/>`_ code.
Here is an example:

.. literalinclude:: ../../benchopt/tests/dummy_benchmark/solvers/python_pgd.py

For solvers that allow access to each iterate of the solution, using ``"callback"``
as a ``sampling_strategy`` implies a slight modification for ``run``. A ``callback``
should be called at each iteration with parameter the current value of the iterate.
Here is an example in the same situation as above:

.. literalinclude:: ../../benchopt/tests/dummy_benchmark/solvers/python_pgd_callback.py
  :pyobject: Solver.run

If your Python solver requires some packages such as `Numba <https://numba.pydata.org/>`_,
Benchopt allows you to list some requirements. The necessary packages should be available
via `conda <https://docs.conda.io/en/latest/>`_ or
`pip <https://packaging.python.org/guides/tool-recommendations/>`_.
See :ref:`specify_requirements`_ for more details on how to specify the requirements for benchopt classes.

.. _r_solvers:

R solver
~~~~~~~~

A solver written in `R <https://www.r-project.org/>`_ needs two files.
A ``.R`` file that contains the solver and a ``.py`` file that knows how to call the
R solver using `Rpy2 <https://pypi.org/project/rpy2/>`_. Only the extensions
should differ between the two files. Here is the Python file:

.. literalinclude:: ../../benchmarks/benchmark_lasso/solvers/r_pgd.py

It uses the R code in:

.. literalinclude:: ../../benchmarks/benchmark_lasso/solvers/r_pgd.R
    :language: R

.. _julia_solvers:

Julia solver
~~~~~~~~~~~~

A solver written in `Julia <https://julialang.org>`_ needs two files.
A ``.jl`` file that contains the solver and a ``.py`` file that knows how to call the
Julia solver using `PyJulia <https://pypi.org/project/julia/>`_. Only the extensions
should differ between the two files. Here is the Python file:

.. literalinclude:: ../../benchmarks/benchmark_lasso/solvers/julia_pgd.py

It uses the Julia code in:

.. literalinclude:: ../../benchmarks/benchmark_lasso/solvers/julia_pgd.jl
    :language: julia

.. admonition:: Installing Julia dependencies

  Note that it is also possible to install ``julia`` dependencies using ``benchopt install`` with the class attribute ``julia_requirements``. This attribute should be a list of package names, whose string are directly passed to ``Pkg.add``.

  In case it is necessary to install dependencies from a GitHub repository, one can use the following format: ``PkgName::https://github.com/org/Pkg.jl#branch_name``. This will be processed to recover both the url and the package name. Note that the ``branch_name`` is optional. Using the ``::`` to specify the ``PkgName`` is necessary to allow ``benchopt`` to check if it is installed in the targeted environment.

.. _source_solvers:

Solver from source
~~~~~~~~~~~~~~~~~~

You can install a package from source in case it is not available
as binaries from the package managers from either Python, R or Julia.

.. note::
    A package available from source may require a C++
    or Fortran compiler.

.. note::

    See for example on the L1 logistic regression benchmark for
    `an example <https://github.com/benchopt/benchmark_logreg_l1/blob/master/solvers/liblinear.py>`_
    that uses a ``'shell'`` as ``install_cmd``.