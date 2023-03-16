from benchopt import BaseSolver


class Solver(BaseSolver):
    name = 'epoch-solver'
    stopping_strategy = 'iteration'

    parameters = {
        "n_epochs": [1, 10, 100]
    }

    def __init__(self, n_epochs):
        self.n_epochs = n_epochs

    def set_objective(self, a, b):
        self.a, self.b = a, b

    def run(self, n_iter):
        # init grad step
        # lipschitz constant is `a**2`
        step = 1 / self.a ** 2  # assuming `a` is not zero
        step *= 1e-2  # make it small to slow down convergence

        x = 0.
        for _ in range(n_iter):

            for _ in range(self.n_epochs):
                grad = self.a * (self.a * x + self.b)
                x -= step * grad

        self.x = x

    @staticmethod
    def get_next(previous):
        "Linear growth for n_iter."
        return previous + 1

    def get_result(self):
        return self.x
