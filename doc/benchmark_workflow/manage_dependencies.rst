.. _manage_dependencies:

Manage dependencies
======================

In order to make it easy to run a new benchmark, benchopt provides an interface
to easily specify and install requirements for the various component of the
benchmarks.

- The minimal requirements that are necessary to run the benchmark are
  specified in ``objective.py``. They can be install using the command
  ``benchopt install --minimal``.

- The requirements that are specific to each ``Dataset/Solver`` can be
  specified in each class, and they can be installed individually by selecting
  the proper component using ``benchopt install -d dataset1 -s solver1``.


.. _specifying_requirements:

Specifying requirements
-----------------------


In order to specify the dependencies, one can add a class attribute ``requirements``.This is
probably due to missing dependency specification. One can also specify the
the install command that should be used to install the dependencies by adding a
class attribute `install_cmd`. This attribute can only take 2 values :

- `conda` (default) : The dependencies will be installed using conda. The class 
  should have a class attribute `requirements` that specifies the dependencies.
- `shell` : The class should have a class attribute `install_script` that specifies
  the shell script that should be run to install the dependencies. Benchopt will
  run this script in the shell and provide the conda environment directory as an
  argument. 


Specifying Dependencies in Benchopt
-----------------------------------

To specify how dependencies should be installed, you can use the ``install_cmd`` class attribute.
This attribute accepts two possible values:

1. ``conda`` (default): Dependencies will be installed using Conda. In this case, you should 
  specify the required dependencies in the ``requirements`` class attribute.

2. ``shell``: This option allows you to provide a custom shell script for installing dependencies. 
  When using this value, you need to set the ``install_script`` class attribute to the path of your shell script.
  Benchopt will execute this script in the shell and pass the Conda environment directory as an argument.

Additionally, to define the dependencies required by your benchmark, you can use the ``requirements`` class attribute. 
This attribute should list all necessary dependencies to ensure smooth execution and reproducibility of your benchmarks.

By properly setting these attributes, you ensure that all dependencies are installed 
correctly. This will help users to run your benchmarks without any issues.




The dependencies should be specified in class attribute `requirements`.\n
Examples:

.. code-block:: python

  requirements = ['pkg'] # conda package `pkg`
  requirements = ['chan:pkg'] # package `pkg` in conda channel `chan`


One might also need to install pip packages. This can be done by using the 
channel `pip` and the `conda` installer. The syntax is the following:

.. code-block:: python

  requirements = ['pip:pkg'] # pip package `pkg`

