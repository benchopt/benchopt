Controlling randomness in Benchopt
=================================

Benchopt provides a mechanism to control randomness across runs, solvers,
datasets and repetitions, by producing deterministic and reproducible seeds.
This page explains how the ``get_seed`` method works and how to use it inside
``Objective``, ``Dataset`` and ``Solver`` classes.

Seed helper
-----------

All benchopt base classes include a seeding mixin.
**Benchopt derives a deterministic seed from the experiment axes you choose.**

This function returns an integer seed computed deterministically from the
benchmark identity and the boolean flags you pass. The seed should be passed
to your RNG constructors (for example ``numpy.random.RandomState`` or
``random.Random``) to obtain deterministic pseudo-random streams.

``get_seed(use_objective=True, use_dataset=True,
           use_solver=True, use_repetition=True)``

Each flag corresponds to an experiment axis that can affect the seed:

- ``use_objective``: include the objective identity.
- ``use_dataset``: include the dataset identity.
- ``use_solver``: include the solver identity.
- ``use_repetition``: include the repetition index.

By toggling these flags, you choose which experimental axes **cause randomness
to change**.

Examples:

- If you want different randomness per repetition but the same randomness for
  all solvers on the same dataset/objective, set
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

We provide an example for custom objective, however, the same logic applies for
custom datasets and solvers.

.. code-block:: python

    from benchopt import BaseObjective
    import numpy as np

    class Objective(BaseObjective):
        name = "example"

        def evaluate_result(self, beta):
            # deterministic seed that depends on objective, dataset, solver,
            # and repetition
            seed = self.get_seed(
                use_objective=True,
                use_dataset=True,
                use_solver=True,
                use_repetition=True
            )
            rng = np.random.RandomState(seed)
            noise = rng.randn(*beta.shape)
            return dict(value=np.sum(beta**2), aux_noise=noise)
