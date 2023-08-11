.. _performance_curves:

Performance curves
==================

The performance of each solver is evaluated for various computational budget.
With "*performance curves*", we refer to the evolution of the performance as a
function of the computational budget.
With benchopt, there are different ways to vary the computational budget
to sample the performance curve.
They are chosen by the ``sampling_strategy`` attribute of each solver.


Sampling strategies
-------------------

1. Using iterations or tolerance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first way is to use ``Solver.sampling_strategy = "iteration"`` or ``Solver.sampling_strategy = "tolerance"``.
This is used for black box solvers, where one can only get the result of the solver for a given number of iterations or for a given numerical tolerance.
This sampling strategy creates curves by calling ``Solver.run(stop_val)`` several times with different values for the ``stop_val`` parameter:

- if the solver's ``sampling_strategy`` is ``"iteration"``, ``stop_val`` is the number of iterations passed to ``run``.
  It increases geometrically by at least 1, starting from 1 with a factor :math:`\rho=1.5`.
  Note that the first call uses a number of iterations of 0.
  The value from one call to the other follows:

  .. math::

    \text{stop_val} = \max(\text{stop_val} + 1, \text{int}(\rho * \text{stop_val}))

- if the solver's ``sampling_strategy`` is ``"tolerance"``, the ``stop_val`` parameter corresponds to the numerical tolerance.
  It decreases geometrically by a factor :math:`\rho=1.5` between each call to ``run``, starting from 1 at the second call.
  Note that the first call uses a tolerance of 1e38.
  The value from one call to the other follows:

  .. math::

    \text{stop_val} = \min(1, \max(\text{stop_val} / \rho, 10^{-15}))


In both cases, if the objective curve is flat (i.e., the variation of the objective between two points is numerically 0), the geometric rate :math:`\rho` is multiplied by 1.2.

Note that the solver is restarted from scratch at each call to ``solver.run``.
For more advanced configurations, the evolution of ``stop_val`` can be controlled on a per solver basis, by implementing a ``Solver.get_next`` method, which receives the current value for tolerance/number of iterations, and returns the next one.

2. Using a callback
~~~~~~~~~~~~~~~~~~~

Restarting the solver from scratch, though inevitable to handle black box solvers, can be costly.

When a solver exposes the intermediate values of the iterates, it is possible to create the curve in a single solver run, by using ``sampling_strategy = "callback"``.
In that case, the argument passed to ``Solver.run`` will be a callable object, ``callback``.
Like with ``sampling_strategy == "iteration"``, the objective is computed after a number of callback's calls that grows geometrically. If the objective was computed after :math:`n` calls, the objective and timing will be computed again when reaching :math:`\max(n+1, \rho * n)` calls to the callback.
The callback makes sure we do not account for objective computation time and also check for convergence every time the objective is computed (as described in the next section).
It returns ``False`` when the solver should be stopped. A classical usage pattern is:

.. code:: python

    def run(self, callback):
        self.x = ... # Initialize iterate

        while callback():
            self.x = ...  # Update iterate

    def get_result(self):
        return {'x': self.x}



When are the solvers stopped?
-----------------------------

For each of the sampling strategies above, the solvers continue running (i.e. the callback returns ``True``, the number of iterations passed to ``Solver.run`` increases or the tolerance passed to ``Solver.run`` decreases) until it the ``StoppingCriterion.should_stop()`` associated to the solver ``Solver.stopping_criterion`` returns ``True``.

This method takes into account the maximal number of runs given as ``--max-runs``, the timeout given by ``--timeout`` and also tries to stop the solver if it has converged.
The convergence of a solver is determined by  the ``StoppingCriterion.check_convergence()`` method, based on the objective curve so far.
There are three ``StoppingCriterion`` implemented in benchopt:

- ``SufficientDescentCriterion(eps, patience)`` considers that the solver has converged when the relative decrease of the objective was less than a tolerance ``eps`` for more than ``patience`` calls to ``check_convergence``.
- ``SufficientProgressCriterion(eps, patience)`` considers that the solver has converged when the objective has not decreased by more than a tolerance ``eps`` for more than ``patience`` calls to ``check_convergence``.
- ``SingleRunCriterion(stop_val)`` only call the solver once with the given stop_val. This criterion designed for methods that converge to a given value, when one aim to benchmark final performance of multiple solvers.
