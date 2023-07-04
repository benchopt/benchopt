
from benchopt.utils.files import temp_benchmark


datasets = [
    (
        "from benchopt import BaseDataset\n"
        "class Dataset(BaseDataset):\n"
        "    name = 'dummy-dataset'\n"
        "    def __init__(self, param=1.):\n"
        "        self.param = param\n"
        "    def get_data(self):\n"
        "        return dict(a=1, b=1)\n"
    ),
]

solvers = [
    (
        "from benchopt import BaseSolver, safe_import_context\n"
        "with safe_import_context() as import_ctx_wrong_name:\n"
        "   import numpy as np\n"
        "class Solver(BaseSolver):\n"
        "   name = 'test_import_ctx'\n"
        "   def set_objective(self, a, b):\n"
        "       self.a, self.b = a, b\n"
        "   def run(self, n_iter):\n"
        "       return -n_iter / 1000\n"
    )
]


objective = (
    "from benchopt import BaseObjective\n"
    "import numpy as np\n"
    "class Objective(BaseObjective):\n"
    "   def set_data(self, a, b):\n"
    "       self.a, self.b = a, b\n"
    "   def get_objective(self):\n"
    "       return dict(a=self.a, b=self.b)\n"
    "   def compute(self, x):\n"
    "       return np.exp(x)\n"
)


with temp_benchmark(objective, datasets, solvers) as temp_bench:
    print(
        temp_bench.name
    )

    print(temp_bench.get_dataset_names())
