from abc import abstractmethod
from benchopt.base import BaseSolver
from benchopt.stopping_criterion import SufficientProgressCriterion


class BaseGridSolver(BaseSolver):
    """A base class to run a solver over a grid of parameters that will be
    plot on the x-axis of Benchopt's plots.
    
    Grid solvers that derive from this class should implement the following
    methods:

    - ``set_objective(self, **objective_parameters)`` function of `BaseSolver`.
      During the call of this function, the grid solver must set the attribute
      ``self.grid_values`` which specifies the grid values. This attribute is a
      flattened array.
    - ``run_grid_value(self, grid_value)``: run the solver at a given value 
      `grid_value` of the grid `self.grid_values`. The result of this function
      will be stored in the attribute `self.result` which stores the result
      at the current value of the grid.

    The class already implements attributes and methods by default so that the 
    method is run over all the grid parameters specified in `self.grid_values`.
    Therefore, the following attributes and methods needs NOT be overloaded:

    - `stopping_strategy`
    - `get_next(self, stop_val)`
    - `run(self, stop_val)`
    - `get_result(self)`
    """

    stopping_strategy = SufficientProgressCriterion(
        patience=2, strategy="iteration"
    )
    
    def __init__(self, **parameters):
        super().__init__(**parameters)
        self.grid_values = None  # grid of parameters value
        self.result = None  # result at the current grid value

    @property
    def grid_values(self):
        raise ValueError(
            "The attribute `self.grid_values` must be set during the call of"
            "the `self.set_objective(**kwargs)` function."
        )
    
    def get_next(self, grid_index):
        return min(grid_index + 1, len(self.grid_values) - 1)

    def run(self, grid_index):
        """Run the solver for one value of the grid. It passes the previous 
        result to `self.run_grid_value(...)` in order to perform warm-starts, 
        etc, ... and replaces it by the new result."""
        self.grid_index = grid_index
        self.result = self.run_grid_value(
            self.grid_values[grid_index], self.result
        )

    @abstractmethod
    def run_grid_value(self, grid_value, prev_result):
        """Runs the solver at a given value `grid_value` of the parameter grid. 
        
        This function must return the solver result corresponding to 
        `grid_value`. The result at the previous grid value can be accessed
        through `prev_result`. If `grid_value` is the first element of the 
        grid, `prev_result` will be passed as a `None` value.
        
        Parameters
        ----------
        grid_value : Any
            Current value in the grid.
        prev_result: Any
            Result at the previous grid value. A `None` is passed if the 
            current grid value is the first one.
        """
        ...

    def get_result(self):
        "Returns the result and its corresponding position in the grid value."
        return (self.result, self.grid_index)