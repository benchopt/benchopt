.. _cli_documentation:

============================
Command line interface (CLI)
============================

The following commands are built using the
`click <https://click.palletsprojects.com/en/8.0.x/>`_ package which provides tab
completion for the command options. You however need to activate shell
completion by following the instructions given in the
`click documentation <https://click.palletsprojects.com/en/8.0.x/shell-completion/#enabling-completion>`_.
For example using BASH shell you need to run:

.. prompt:: bash $

    eval "$(_BENCHOPT_COMPLETE=bash_source benchopt)"


The `benchopt` command also comes with tab completion for the solver name
and the dataset name.

.. admonition:: Optional parameters syntax

    For some CLI parameters (solver, objective,
    dataset), additional values can be given with the following syntax:

    .. code-block:: bash

        # Run a particular solver with a particular set of parameters:
        --solver solver_name[param_1=method_name, param_2=100]
        # To select a grid of parameters, the following syntax is allowed:
        --solver solver_name[param_1=[True, False]]
        # For objects with only one parameter, the name can be omitted:
        --solver solver_name[True, False]
        # For more advanced selections over multiple parameters, use:
        --solver solver_name["param_1,param_2"=[(True, 100), (False, 1000)]]


.. click:: benchopt.cli:benchopt
   :prog: benchopt
   :nested: full

