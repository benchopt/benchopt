.. _controlling_randomness:

Reproducibility helpers: seeding and run artifacts
===================================================

Benchopt provides a mechanism to control randomness across runs, solvers,
datasets and repetitions, by producing deterministic and reproducible seeds.
This page explains how the ``get_seed`` method works and how to use it inside
``Objective``, ``Dataset`` and ``Solver`` classes.

Seed helper
-----------

All benchopt base classes provide a ``get_seed``
method, to derive **a deterministic seed from the chosen experiment axes.**

This function returns an integer seed computed deterministically from the
benchmark's global seed and the boolean flags you pass. The seed can then
be used to seed random number generators (*e.g.* ``numpy.random.RandomState``,
or ``torch.manual_seed``) to obtain deterministic pseudo-random streams.

.. code-block:: python

     seed = self.get_seed(use_objective=True, use_dataset=True,
                           use_solver=True, use_repetition=True)

Each argument is a flag which corresponds to an axis of the experiment. Setting the
flag to ``True`` makes the seed vary when this element changes.

- ``use_objective``: seed changes when the objective vary.
- ``use_dataset``: seed changes when the dataset vary.
- ``use_solver``: seed changes when the solver vary.
- ``use_repetition``: seed changes on each the repetition.

The objective, dataset and solver are considered to vary when their name
or parameters change. This means that if you change the parameters of a
solver, it will be considered as a different solver and the seed will change if
``use_solver=True``.

By toggling these flags, you choose which experimental axes cause randomness
to change. By default, the generated seed is independent from the combination
of ``Dataset``, ``Objective``, ``Solver`` and across repetitions.

Examples:

- If you want different randomness per repetition but the same randomness for
  all solvers for a given ``(dataset, objective)`` couple, set
  ``use_solver=False`` and ``use_repetition=True``.
- If you want the same randomness for all repetitions and solvers, set
  ``use_repetition=False`` and ``use_solver=False``.

How seeding is provided
-----------------------

The user may provide a **main seed** to the benchmark via the ``--seed`` flag.
By default, this seed is set to 0, to avoid disrupting caching. This means that
During the benchmark, Benchopt calls ``set_seed`` to combine the main seed with
the components selected by the flags (objective, dataset, solver, repetition).
This produces a unique, reproducible per-run integer seed.
During the benchmark, Benchopt calls ``set_seed`` to combine the main seed with
the components selected by the flags (objective, dataset, solver, repetition).
This produces a unique, reproducible per-run integer seed.

When to call get_seed
---------------------

Call ``get_seed`` **only during execution** of the benchmark, ie. for Solver
from ``set_objective``, for Dataset from ``get_data``, and for Objective from
and ``set_data`` and ``get_objective``.

Do **not** call it at import time or during class definition — at that stage,
the benchmark runner has not yet created the correct runtime context, and the
seed has not been initialized.

.. note::

    When ``get_data`` is called by :ref:`benchopt prepare <prepare_datasets>`,
    only the dataset is known. A ``Dataset`` may therefore only call
    ``get_seed(use_dataset=True)`` from ``get_data``; requesting the objective,
    solver or repetition seed raises an error, since these are not defined at
    preparation time. Use the same ``--seed`` for ``prepare`` and ``run`` so the
    prepared data matches the run.

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
            # Get a deterministic seed that depends on objective, dataset, solver,
            # and repetition
            seed = self.get_seed(
                use_objective=True,
                use_dataset=True,
                use_solver=False,
                use_repetition=True
            )

            # Use the seed to create a random number generator and generate noise.
            rng = np.random.RandomState(seed)
            noise = rng.randn(*beta.shape)
            return dict(X=self.X, aux_noise=noise)

.. _run_artifacts:

Saving run artifacts
--------------------

All benchopt base classes also provide a ``get_run_output_path`` method that
returns a directory **unique to the current run** (dataset x objective x solver
x repetition). Use it to save per-run artifacts such as intermediate models,
diagnostic plots, or convergence logs.

.. code-block:: python

    class Solver(BaseSolver):
        name = "my-solver"

        def run(self, n_iter):
            # … training loop …
            output_dir = self.get_run_output_path()
            np.save(output_dir / "weights.npy", self.weights)

The directory is created automatically on first call and lives under
``<benchmark>/outputs/<run_name>/<dataset>/<objective>/<solver>/rep_<k>/``.

Like ``get_seed``, this method is available on ``Dataset``, ``Objective``, and
``Solver``, and must be called during execution (not at import time or class
definition). It raises ``RuntimeError`` when called outside of a
``benchopt run`` invocation (e.g. during ``benchopt test``).

.. _checkpoints:

Checkpointing a training
------------------------

The directory given by ``get_run_output_path`` changes at each call to
``benchopt run``. To find the state of a training again in a later run, use
``get_checkpoint_path``. It returns a directory that only depends on what
defines the training, so an interrupted training can be resumed, and a
finished one can be evaluated again without training.

.. code-block:: python

    class Solver(BaseSolver):
        name = "my-solver"
        sampling_strategy = "run_once"

        def run(self, _):
            checkpoint = self.get_checkpoint_path() / "checkpoint.pt"
            # ``fit`` loads ``checkpoint`` if it exists, starts from the
            # epoch it stores, and saves it as the training goes.
            self.model = fit(self.X, self.y, checkpoint=checkpoint)

The directory is named with a hash of the seed, the repetition, the code of
the dataset and of the solver, and the parameters of the three components. It
lives in the cache folder of the benchmark, under ``checkpoints/``, also with
``--no-cache``. With ``benchopt run --checkpoint off``, it is a temporary
directory that lasts for the run, so the code above needs no guard and no
checkpoint is reused nor kept.

Some parameters change how a model is evaluated but not how it is trained,
like the number of samples drawn to score it. List them in the
``eval_parameters`` of the ``Dataset``, ``Objective`` or ``Solver`` that
defines them. They are left out of the name of the directory, so the runs that
only differ by them share one training.

.. code-block:: python

    class Objective(BaseObjective):
        name = "my-objective"
        parameters = {"reg": [0.1, 1], "n_eval": [100, 1000]}
        eval_parameters = ("n_eval",)

The code of the objective is also left out, so a new metric can be computed
from the existing checkpoints.

.. warning::

    benchopt cannot check these choices. A checkpoint is reused silently when
    a parameter listed in ``eval_parameters`` does change the training, or
    when the training code changes outside of the files of the dataset and of
    the solver. Use ``benchopt run --checkpoint refresh`` to remove the
    checkpoints of the selected runs and train them again.

The solver writes its files itself. Write to a temporary name, then rename it
with ``os.replace``, so that a job killed while saving does not leave a
corrupt checkpoint.

.. _callback_checkpoints:

Checkpoints with a callback
~~~~~~~~~~~~~~~~~~~~~~~~~~~

With ``sampling_strategy = "callback"``, one training gives a whole curve.
Here benchopt stores the checkpoints itself, with the state of the callback,
so that a restarted run gives the same curve as an uninterrupted one. The
solver gives its checkpoint to the callback, and reads the one to restart
from in ``self.checkpoint_``, which is ``None`` for a fresh start.

.. code-block:: python

    class Solver(BaseSolver):
        name = "my-solver"
        sampling_strategy = "callback"

        def run(self, callback):
            model, optimizer = build(self.X)
            if self.checkpoint_ is not None:
                model.load_state_dict(self.checkpoint_["model"])
                optimizer.load_state_dict(self.checkpoint_["optimizer"])

            def checkpoint():
                return dict(model=model.state_dict(),
                            optimizer=optimizer.state_dict())

            while callback(checkpoint=checkpoint):
                train_one_step(model, optimizer)

The checkpoint is any object that can be pickled, or a function without
argument that returns it. The function is only called when benchopt stores the
checkpoint: each time the solver is evaluated, and every 10 minutes in between
(see ``checkpoint_interval`` below).
It must hold all that the solver needs to continue: the model, the optimizer,
the schedule and the state of the random generators.

When a run starts and checkpoints exist for its training:

- the points of the curve already evaluated for this run are reused. The
  other ones are evaluated from their checkpoint, e.g. for a run that only
  differs by a parameter listed in ``eval_parameters``. For this, ``run`` is
  called with ``checkpoint_`` set and stopped at its first call to the
  callback. The last point is always evaluated this way.
- the solver then restarts from its last checkpoint, with the iteration and
  the time of the callback restored.

The callback must be called before the first step of the solver, as in the
``while callback(...)`` loop above. Otherwise, a point evaluated from its
checkpoint is one step late.

The stored evaluations are reused even if the code of the objective changed
since, with a warning. Use ``benchopt run --checkpoint rescore`` to evaluate
all the checkpoints again, e.g. to add a metric to finished runs without
training.

Two class attributes tune what is stored. They are set on the ``Solver``, or
on the ``Objective`` for all the solvers:

- ``checkpoint_keep = k`` only keeps the checkpoints of the ``k`` last points
  of the curve. By default, they are all kept. The points whose checkpoint
  was removed cannot be evaluated again: they are missing from the curve of a
  run that needs to.
- ``checkpoint_interval`` is the time in seconds between two checkpoints
  stored between the evaluations, 600 by default. A killed run loses at most
  this training time.
