.. _iterative_solvers:

Evaluating an iterative method
==============================

.. note::
   **For ML benchmarks without iterative evaluation:** If you are benchmarking
   machine learning methods where each solver runs once to completion (e.g.,
   comparing scikit-learn estimators), you can skip performance curves entirely
   by setting ``sampling_strategy = "run_once"`` in your ``Objective`` class.
   See :ref:`write_benchmark` for more details on setting up ML benchmarks.

   .. code-block:: python

      class Objective(BaseObjective):
          sampling_strategy = "run_once"

Performance curves are primarily useful for **iterative optimization methods**,
where you want to track how the objective value evolves as computational budget
increases (e.g., number of iterations, tolerance, or CPU time).

The performance of each solver is evaluated for various computational budgets.
With "*performance curves*", we refer to the evolution of the performance as a
function of the computational budget.

With benchopt, there are different ways to vary the computational budget
to sample the performance curve.
They are chosen by the ``sampling_strategy`` attribute of each solver, or if
specified, the ``strategy`` parameter of the ``stopping_criterion`` of the
solver. They can also be set for all the solvers in the ``Objective``, as
described in :ref:`global_strategy`.

When varying the computational budget, there are often the need to be able to
stop the solver when it has converged, to avoid wasting resources on already
converged methods.
This is handled by the ``stopping_criterion`` attribute of each solver, which
is described in the last section of this document :ref:`stopping_criterion`.


Sampling strategies
-------------------

0. Running once (no performance curve)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For benchmarks where solvers run to completion without intermediate evaluation
(typical in ML benchmarks), use ``sampling_strategy = "run_once"``.
The solver's ``run`` method is called exactly once, and no convergence curve
is generated. This is ideal for comparing final performance of different methods.

See :ref:`write_benchmark` for a complete guide on setting up ML benchmarks.


1. Using iterations or tolerance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first way is to use ``Solver.sampling_strategy = "iteration"`` or ``Solver.sampling_strategy = "tolerance"``.
This is used for black-box solvers, where one can only get the result of the solver for a given number of iterations or for a given numerical tolerance.
This sampling strategy creates curves by calling ``Solver.run(stop_val)`` several times with different values for the ``stop_val`` parameter:

- if the solver's ``sampling_strategy`` is ``"iteration"``, ``stop_val`` is the number of iterations passed to ``run``.
  It increases geometrically by at least 1, starting from 1 with a factor :math:`\rho=1.5`.
  Note that the first call uses a number of iterations of 0.
  The value from one call to the other follows:

  .. math::

    \text{stop\_val} = \max(\text{stop\_val} + 1, \text{int}(\rho * \text{stop\_val}))

- if the solver's ``sampling_strategy`` is ``"tolerance"``, the ``stop_val`` parameter corresponds to the numerical tolerance.
  It decreases geometrically by a factor :math:`\rho=1.5` between each call to ``run``, starting from 1 at the second call.
  Note that the first call uses a tolerance of 1e38.
  The value from one call to the other follows:

  .. math::

    \text{stop\_val} = \min(1, \max(\text{stop\_val} / \rho, 10^{-15}))


In both cases, if the objective curve is flat (i.e., the variation of the objective between two points is numerically 0), the geometric rate :math:`\rho` is multiplied by 1.2.

Note that the solver is restarted from scratch at each call to ``solver.run``.
The formula to compute the next ``stop_val`` can be changed, as described in :ref:`sampling_strategy`.

.. _callback:

2. Using a callback
~~~~~~~~~~~~~~~~~~~

Restarting the solver from scratch, though inevitable to handle black box solvers, can be costly.

When a solver exposes the intermediate values of the iterates, it is possible to create the curve in a single solver run, by using ``sampling_strategy = "callback"``.
In that case, the argument passed to ``Solver.run`` will be a callable object, ``callback``.
This callback is created and managed by ``benchopt``.
Like with ``sampling_strategy = "iteration"``, the objective is computed after a number of callback's calls that grows geometrically. If the objective was computed after :math:`n` calls, the objective and timing will be computed again when reaching :math:`\max(n+1, \rho * n)` calls to the callback.
The callback makes sure we do not account for objective computation time and also check for convergence every time the objective is computed (as described in the next section).
It returns ``False`` when the solver should be stopped. A classical usage pattern is:

.. code:: python

    def run(self, callback):
        self.x = ... # Initialize iterate

        while callback():
            self.x = ...  # Update iterate

    def get_result(self):
        return {'x': self.x}

.. _sampling_strategy:

3. Changing the strategy to grow the computational budget (:code:`stop_val`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The way benchopt varies the computational budget :code:`stop_val` can be
configured on a per-solver basis. This is done by implementing a ``get_next``
method in the ``Solver`` class. This method takes as input the previous value
where the objective function has been logged, and outputs the next one. For
instance, if a solver needs to be evaluated every 10 iterations, we would have

.. code-block::

    class Solver(BaseSolver):
        ...
        def get_next(self, stop_val):
            return stop_val + 10

This example allows to set a linear growth for the solver computational budget, instead of the default geometric growth.
Implementing ``get_next`` in the ``Objective`` changes the growth for all the solvers that do not implement their own.

.. _stopping_criterion:

When are the solvers stopped?
-----------------------------

For each of the sampling strategies above, the solvers continue running (i.e. the callback returns ``True``, the number of iterations/tolerance passed to ``Solver.run`` increases/decreases) until the ``StoppingCriterion.should_stop()`` associated to the solver ``Solver.stopping_criterion`` returns ``True``.

This method takes into account the maximal number of runs given as ``--max-runs``, the timeout given by ``--timeout`` and also tries to stop the solver if it has converged.
The convergence of a solver is determined by the ``StoppingCriterion.check_convergence()`` method, based on the objective curve so far.
There are four ``StoppingCriterion`` implemented in benchopt:

- ``SingleRunCriterion(stop_val)`` only calls the solver once with the given stop_val. This criterion is designed for methods that converge to a given value, when one aims to benchmark final performance of multiple solvers. Its strategy is ``"run_once"``, or ``"callback"`` for solvers whose ``run`` takes a callback, which is then called ``stop_val`` times. ``"iteration"`` is the same as ``"run_once"``, and ``"tolerance"`` is not supported.
- ``NoCriterion()`` runs the solver for a fixed number of steps, given by the ``--max-runs`` argument. This criterion deactivate the checks for convergence.
- ``SufficientDescentCriterion(eps, patience, key_to_monitor, minimize)`` considers that the solver has converged when the relative decrease of the objective was less than a tolerance ``eps`` for more than ``patience`` calls to ``check_convergence``. The ``key_to_monitor`` is the key of the objective dictionary to monitor. By default, it is set to ``value``. The ``minimize`` parameter indicates whether the monitored key should be minimized (``True``, default) or maximized (``False``).
- ``SufficientProgressCriterion(eps, patience, key_to_monitor, minimize)`` considers that the solver has converged when the objective has not decreased by more than a tolerance ``eps`` for more than ``patience`` calls to ``check_convergence``. The ``key_to_monitor`` is the key of the objective dictionary to monitor. By default, it is set to ``value``. The ``minimize`` parameter indicates whether the monitored key should be minimized (``True``, default) or maximized (``False``).

.. _global_strategy:

Setting the sampling strategy and stopping criterion globally
-------------------------------------------------------------

The sampling strategy, the stopping criterion and ``get_next`` can be set for all the solvers in the ``Objective`` class:

.. code-block:: python

    class Objective(BaseObjective):
        sampling_strategy = "callback"  # or "iteration", "tolerance", "run_once"
        stopping_criterion = SufficientProgressCriterion(
            eps=1e-5, patience=5, key_to_monitor="value", minimize=True
        )

        def get_next(self, stop_val):
            return stop_val + 10

This avoids repeating these settings in each solver when most solvers use the same ones.
They are resolved for each run, as follows:

- A solver's own ``sampling_strategy``, ``stopping_criterion`` or ``get_next`` takes precedence over the objective's.
- A solver whose strategy is ``"run_once"`` is run once, whatever the objective's criterion.
- Without any setting, solvers use ``sampling_strategy = "iteration"`` and ``SufficientProgressCriterion()``.

A solver that sets ``sampling_strategy`` and a ``stopping_criterion`` with another ``strategy`` is reported as an error, and its runs are skipped.

.. _custom_stopping_criterion:

Implementing a new stopping criterion
-------------------------------------

A new criterion subclasses ``StoppingCriterion`` and implements ``check_convergence``.
This method receives the list of the objective dictionaries computed so far.
It returns whether the solver should stop, and its progress in ``[0, 1]``, which is displayed in the terminal.
The base class already handles ``--max-runs``, ``--timeout`` and diverging solvers.

Benchopt copies the criterion for each run, by calling its constructor with the parameters it received.
The constructor must thus pass all its parameters to ``super().__init__``, with ``strategy``, ``key_to_monitor`` and ``minimize``:

.. code-block:: python

    from benchopt.stopping_criterion import StoppingCriterion


    class ThresholdCriterion(StoppingCriterion):
        """Stop once the monitored value goes below a threshold."""

        def __init__(self, threshold, strategy=None, key_to_monitor="value",
                     minimize=True):
            self.threshold = threshold
            super().__init__(
                threshold=threshold, strategy=strategy,
                key_to_monitor=key_to_monitor, minimize=minimize,
            )

        def check_convergence(self, objective_list):
            # `key_to_monitor_` is the key in the objective dictionaries.
            value = objective_list[-1][self.key_to_monitor_]
            stop = value < self.threshold
            return stop, float(stop)

The criterion can be defined in ``benchmark_utils`` and used in a solver or in the objective, like the ones provided by benchopt:

.. code-block:: python

    from benchmark_utils import ThresholdCriterion

    class Solver(BaseSolver):
        stopping_criterion = ThresholdCriterion(threshold=1e-6)
