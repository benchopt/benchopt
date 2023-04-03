from benchopt import BaseObjective


class Objective(BaseObjective):

    name = "1D OLS"

    def set_data(self, a, b):
        self.a, self.b = a, b

    def compute(self, x):
        return {
            'value': 0.5 * (self.a * x + self.b) ** 2
        }

    def get_objective(self):
        return dict(a=self.a, b=self.b)
