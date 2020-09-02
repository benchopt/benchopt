import pandas as pd
from benchopt.base import CommandLineSolver
from benchopt.util import safe_import_context, import_shell_cmd

with safe_import_context() as import_ctx:
    train_cmd = import_shell_cmd('train')


class Solver(CommandLineSolver):
    name = 'Liblinear'
    stop_strategy = 'tolerance'

    install_cmd = 'shell'
    install_script = 'install_liblinear.sh'

    def set_objective(self, X, y, lmbd):

        # The regularization parameter is passed directly to the command line
        # so we store it for latter.
        self.lmbd = lmbd

        # Dump the large arrays to a file and store its name
        n_samples = X.shape[0]
        with open(self.data_filename, 'w') as f:
            for i in range(n_samples):
                line = f"{'+1' if y[i] > 0 else '-1'} "
                line += " ".join([f"{c[0] + 1}:{c[1]:.12f}"
                                  for c in enumerate(X[i])])
                line += "\n"

                f.write(line)

    def run(self, tolerance):
        train_cmd(f"-q -s 6 -B -1 -c {1 / self.lmbd} "
                  f"-e {tolerance} {self.data_filename} "
                  f"{self.model_filename}")

    def get_result(self):
        df = pd.read_csv(self.model_filename, header=5)
        return df.w.to_numpy()
