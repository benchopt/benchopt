.. _convergence_curves:

Sampling of convergence curves: ``stopping_strategy``
=====================================================

There are two ways to create a convergence curve for a given solver, controlled by the ``stopping_strategy`` attribute of the solver.

1. Using iterations or tolerance
--------------------------------

The first way, used for black box solvers, is to create curves by calling the ``Solver.run`` method several times for each solver with different values for the ``stop_val`` parameter.
The solver is restarted from scratch at each call to ``run``.
- if the solver's ``stopping_strategy`` is ``"iteration"``, the number of iterations passed to ``run`` increases geometrically from 1 with a factor XXX, eventually switching to XXX if the curves becomes flat., and the
- if the solver's ``stopping_strategy`` is ``"tolerance"``, the ``stop_val`` parameter corresponds the the tolerance, and decreases geometrically by a factor of XXX between each call to ``run``, starting from XXX.


The evolution of ``stop_val`` can be controlled on a solver level, by implementing a  ``Solver.get_next`` method, which receives the current value for tolerance/number of iterations, and should return the next one.

2. Using a callback
-------------------

The solution above can be costly. When the solvers expose the intermediate values of the iterates, it is possible to create the curve in a single solver run, by using a callback method.
XXX link to solver code.

When are the convergence curves considered complete: ``StoppingCriterion``
==========================================================================

The sampling of points on the curve stop when:
- the timeout is reached
- the objective value stops decreasing XXX StoppingCriterion
- the callback says so XXX






XXX best point on curve ?