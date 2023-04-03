from benchopt import BaseSolver


class Solver(BaseSolver):
    name = "gradient-descent"

    parameters = {
        "param_1, param_2": [(1, 2)]
    }

    def __init__(self, param_1, param_10):
        pass

    def set_objective(self, a, b):
        self.a, self.b = a, b

    def run(self, n_iter):
        a, b = self.a, self.b

        step = 1 / self.a ** 2
        x = 0.
        for _ in range(n_iter):
            grad = self.a * (a * x + b)
            x -= step * grad

        self.x = x

    def get_result(self):
        return self.x
