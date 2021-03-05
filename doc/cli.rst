.. _cli_documentation:

==========================================
Command Line Interface (CLI) Documentation
==========================================

The following commands are built using the
`click <https://click.palletsprojects.com/en/7.x/>`_ package which provides tab
completion for the command options. You however need to activate shell
completion by following the instructions given in the
`click documentation <https://click.palletsprojects.com/en/7.x/bashcomplete/#activation>`_.
For example using BASH shell you need to run:

.. code-block::

    eval "$(_BENCHOPT_COMPLETE=source_bash benchopt)"


The `benchopt` command also comes with tab completion for the solver name
and the dataset name.

.. click:: benchopt.cli:benchopt
   :prog: benchopt
   :nested: full

