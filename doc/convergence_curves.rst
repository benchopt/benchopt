.. _convergence_curves:

Sampling of convergence curves: ``stopping_strategy``
=====================================================

For each solver, there are two ways to create a convergence curve.
They are chosen by the ``stopping_strategy`` attribute of the solver.

1. Using iterations or tolerance
--------------------------------


The first way is to use ``Solver.stopping_strategy = "iteration"`` or ``Solver.stopping_strategy = "tolerance"``.
This is used for black box solvers, where one can only get the result of the solver for a given number of iterations or numerical tolerance.
This stopping strategy creates curves by calling ``Solver.run(stop_val)`` several times with different values for the ``stop_val`` parameter:
- if the solver's ``stopping_strategy`` is ``"iteration"``, the number of iterations passed to ``run`` increases geometrically by at least 1, starting from 1 with a factor 1.5.
If the objective curve becomes too flat, the geometric factor is multiplied by 1.2.
- if the solver's ``stopping_strategy`` is ``"tolerance"``, the ``stop_val`` parameter corresponds to the tolerance, and decreases geometrically by a factor of 1.5 between each call to ``run``, starting from 1. The first call uses a tolerance of 1e38.

Note that the solver is started from scratch at each call to ``solver.run``.
For more advanced configurations, the evolution of ``stop_val`` can be controlled on a per solver basis, by implementing a static  ``Solver.get_next`` method, which receives the current value for tolerance/number of iterations, and returns the next one.

2. Using a callback
-------------------

The solution above can be costly.
When a solver exposes the intermediate values of the iterates, it is possible to create the curve in a single solver run, by using a callback method.
XXX link to solver code.

When are the convergence curves considered complete: ``StoppingCriterion``
==========================================================================

The sampling of points on the curve stop when:
- the timeout is reached
- the objective value stops decreasing XXX StoppingCriterion
- the callback says so XXX






XXX best point on curve ?