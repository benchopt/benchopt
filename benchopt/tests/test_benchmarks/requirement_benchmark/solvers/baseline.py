from benchopt import BaseSolver


class Solver(BaseSolver):
    name = 'Dummy solver'
    stopping_strategy = "callback"

    def set_objective(self, X):
        self.X = X

    def run(self, callback):

        while callback(0):
            pass

        self.w = 0

    def get_result(self):
        return self.w
