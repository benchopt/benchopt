from benchopt import BaseObjective


class Objective(BaseObjective):
    name = "1D Quadratic"

    def set_data(self, a, b):
        self.a, self.b = a, b

    def get_one_solution(self):
        return 0.

    def compute(self, x):
        obj_val = 0.5 * (self.a * x + self.b) ** 2 + 1

        return dict(value=obj_val)

    def get_objective(self):
        return dict(a=self.a, b=self.b)
