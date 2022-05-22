from benchopt import BaseObjective, safe_import_context

with safe_import_context() as import_ctx:
    # your dependencies here
    pass


class Objective(BaseObjective):
    name = "{name}"

    def __init__(self):
        pass

    def set_data(self):
        pass

    def compute(self):
        return dict()

    def to_dict(self):
        return dict()
