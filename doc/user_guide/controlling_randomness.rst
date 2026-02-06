.. _controlling_randomness:

Controlling randomness in Benchopt
=================================

Benchopt provides a mechanism to control randomness across runs, solvers,
datasets and repetitions, by producing deterministic and reproducible seeds.
This page explains how the ``get_seed`` method works and how to use it inside
``Objective``, ``Dataset`` and ``Solver`` classes.

Seed helper
-----------

All benchopt base classes include a seeding mixin which provides a ``get_seed``
method, to derive **a deterministic seed from the chosen experiment axes.**

This function returns an integer seed computed deterministically from the
benchmark identity and the boolean flags you pass. The seed should then
be used to seed random number generators (*e.g.* ``numpy.random.RandomState``,
or ``torch.manual_seed``) to obtain deterministic pseudo-random streams.

``get_seed(use_objective=True, use_dataset=True,
           use_solver=True, use_repetition=True)``

Each argument is a flag which corresponds to an axis of the experiment. Setting the
flag to ``True`` makes the seed vary when this element changes.

- ``use_objective``: include the objective identity.
- ``use_dataset``: include the dataset identity.
- ``use_solver``: include the solver identity.
- ``use_repetition``: include the repetition index.

By toggling these flags, you choose which experimental axes cause randomness
to change. By default, the generated seed is different for each combination of
``Dataset``, ``Objective``, ``Solver`` and varies across repetition.

Examples:

- If you want different randomness per repetition but the same randomness for
  all solvers for a given ``(dataset, objective)`` couple, set
  ``use_solver=False`` and ``use_repetition=True``.
- If you want the same randomness for all repetitions and solvers, set
  ``use_repetition=False`` and ``use_solver=False``.

How seeding is provided
-----------------------

The user may provide a **master seed** to the benchmark via the ``--seed`` flag.

During the benchmark, Benchopt calls ``set_seed`` to combine the master seed with
the identities selected by the flags (objective, dataset, solver, repetition).
This produces a unique, reproducible per-run seed.

When to call get_seed
---------------------

Call ``get_seed`` **only during execution** of the benchmark (for example inside
``get_data``, ``evaluate_result`` or ``run``).

Do **not** call it at import time or during class definition — at that stage,
the benchmark runner has not yet created the correct runtime context, and the
seed has not been initialized.

Examples
~~~~~~~~

We provide an example for custom ``Objective``, however, the same logic applies for
``Dataset`` and ``Solver`` objects.

.. code-block:: python

    from benchopt import BaseObjective
    import numpy as np

    class Objective(BaseObjective):
        name = "example"

        def get_objective(self):
            # deterministic seed that depends on objective, dataset, solver,
            # and repetition
            seed = self.get_seed(
                use_objective=True,
                use_dataset=True,
                use_solver=False,
                use_repetition=True
            )
            rng = np.random.RandomState(seed)
            noise = rng.randn(*beta.shape)
            return dict(X=self.X, aux_noise=noise)
