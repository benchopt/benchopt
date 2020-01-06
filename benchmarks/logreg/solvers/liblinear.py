import pandas as pd
from benchopt.base import CommandLineSolver


class Solver(CommandLineSolver):
    name = 'Liblinear'
    sampling_strategy = 'tolerance'

    install_cmd = 'bash'
    cmd_name = 'train'
    install_script = 'install_liblinear.sh'

    def dump_objective(self, X, y, lmbd):

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

    def get_command_line(self, tolerance):
        cmd = (f"train -q -s 6 -B -1 -c {1 / self.lmbd} "
               f"-e {tolerance} {self.data_filename} "
               f"{self.model_filename}")
        return cmd

    def get_result(self):
        df = pd.read_csv(self.model_filename, header=5)
        return df.w.to_numpy()
