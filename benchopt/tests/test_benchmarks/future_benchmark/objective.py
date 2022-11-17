from benchopt import BaseObjective


class Objective(BaseObjective):
    min_benchopt_version = "99.0.0"

    def set_data(self):
        pass

    def get_objective(self):
        pass

    def compute(self, beta):
        pass
