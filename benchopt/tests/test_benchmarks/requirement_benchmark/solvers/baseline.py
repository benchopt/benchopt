from benchopt import BaseSolver


class Solver(BaseSolver):
    name = 'Dummy solver'
    sampling_strategy = "callback"

    def set_objective(self, X):
        self.X = X

    def run(self, callback):
        self.w = 0
        while callback(self.get_result()):
            pass

    def get_result(self):
        return {'beta': self.w}
