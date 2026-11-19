.. _contrib_doc:

How to contribute
=================


Bug report and feature request
------------------------------

We use benchopt `GitHub repo <https://github.com/benchopt/benchopt/issues>`_ to track all bugs and feature requests; feel free to open
an issue if you have found a bug or wish to see a feature implemented.


.. _contrib_policy:

Contribution policy
-------------------

The goal of benchopt is not only to build a tool, but also to build a
community around best practices for benchmarking. Contributing is a way to
join this community: discussing designs, reviewing each other's work, and
sharing what makes a benchmark reliable. benchopt is maintained by a small
team, and every pull request is reviewed by hand. We want contributions from
people who are interested in the project and who discuss their changes with
us. Please follow these guidelines:

- **Discuss before coding.** For anything beyond a typo or a small fix,
  comment on the issue first and say how you plan to tackle it. We can then
  agree on the design before you spend time on it, and two people do not work
  on the same issue. Do not hesitate to tell us about the benchmarks you
  develop with benchopt: knowing your use case helps us understand the issue
  and find the right design.

- **Good first issues are kept for newcomers.** The code change of an issue
  labeled ``good first issue`` is often small. We keep these issues as an entry
  point for people who want to get involved with benchopt, through the
  discussion and the reviews.

- **Own your changes.** You can use AI tools to help you write code, tests or
  documentation. You remain the author: you should understand every line of
  your pull request, be able to explain your choices, and answer the review
  comments yourself.

- **No automated contributions.** We close pull requests and comments opened
  in bulk by automated agents, without a person engaging in the discussion.

When in doubt, ask on the issue. We are happy to help you get started.


Code contribution
-----------------

The preferred way to contribute to benchopt is to fork the `main
repository <https://github.com/benchopt/benchopt/>`__ on GitHub,
then submit a "Pull Request" (PR).

In the first few steps, we explain how to locally install benchopt, and
how to set up your git repository:

1. `Create an account <https://github.com/join>`_ on
   GitHub if you do not already have one.

2. Fork the `project repository
   <https://github.com/benchopt/benchopt>`__: click on the 'Fork'
   button near the top of the page. This creates a copy of the code under your
   account on the GitHub user account. For more details on how to fork a
   repository see `this guide <https://help.github.com/articles/fork-a-repo/>`_.

3. Clone your fork of the benchopt repo from your GitHub account to your
   local disk:

   .. prompt:: bash $

      git clone git@github.com:YourLogin/benchopt.git
      cd benchopt

.. _upstream:

4. Add the ``upstream`` remote. This saves a reference to the main
   benchopt repository, which you can use to keep your repository
   synchronized with the latest changes:

   .. prompt:: bash $

        git remote add upstream https://github.com/benchopt/benchopt

5. Check that the `upstream` and `origin` remote aliases are configured correctly
   by running `git remote -v` which should display::

        origin	git@github.com:YourLogin/benchopt.git (fetch)
        origin	git@github.com:YourLogin/benchopt.git (push)
        upstream	https://github.com/benchopt/benchopt (fetch)
        upstream	https://github.com/benchopt/benchopt (push)


You should now have a working installation of benchopt, and your git
repository properly configured. The next steps now describe the process of
modifying code and submitting a PR:

6. Synchronize your ``main`` branch with the ``upstream/main`` branch,
   more details on `GitHub Docs <https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/syncing-a-fork>`_:

   .. prompt:: bash $

        git switch main
        git fetch upstream
        git merge upstream/main

7. Create a feature branch to hold your development changes:

   .. prompt:: bash $

        git switch -c my_feature

   and start making changes. Always use a feature branch. It's good
   practice to never work on the ``main`` branch!

8. Develop the feature on your feature branch on your computer, using Git to
   do the version control. When you're done editing, add changed files using
   ``git add`` and then ``git commit``:

   .. prompt:: bash $

      git add modified_files
      git commit

   to record your changes in Git, then push the changes to your GitHub
   account with:

   .. prompt:: bash $

      git push -u origin my_feature

9. Follow `these <https://help.github.com/articles/creating-a-pull-request-from-a-fork>`_ instructions
   to create a pull request from your fork.

.. note::

    It is often helpful to keep your local feature branch synchronized with the latest
    changes of the main benchopt repository:

    .. prompt:: bash $

        git fetch upstream
        git merge upstream/main


Documentation
-------------

We are glad to accept any sort of documentation: function docstrings,
reStructuredText documents (like this one), tutorials, etc. reStructuredText
documents live in the source code repository under the ``doc/`` directory.

You can edit the documentation using any text editor, and then generate the
HTML output by typing, in a shell:

.. prompt:: bash $

    pip install benchopt[doc]
    cd doc/
    make html
    firefox _build/html/index.html
