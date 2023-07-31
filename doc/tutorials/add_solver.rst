.. _add_solver:

Add a solver
============


- walk you through the cornerstones of adding a new solver
- objective: add a ``skglm`` to benchmark L2 logistic regression


- preliminary
    - solver lives in standalone python file
    - solver is class with a name

- implementation
    - constructor for getting parameters
    - set_objective specify the setup (combination of dataset and objective parameters)
    - get_results
        called by objective to evaluate metrics

- metadata
    - install requirements
    - docstring for details about the solver

- refinement
    - warm_up
    - skip
