"Helper function for colored terminal outputs"
import shutil
import ctypes
import platform

from ..config import DEBUG


MIN_LINE_LENGTH = 20
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)

CROSS = u'\u2717'
TICK = u'\u2713'


STATUS = {
    'error': ("error", RED),
    'diverged': ("diverged", RED),
    'not installed': ('not installed', RED),
    'interrupted': ("interrupted", YELLOW),
    'skip': ('skip', YELLOW),
    'timeout': ("done (timeout)", YELLOW),
    'max_runs': ("done (not enough run)", YELLOW),
    'done': ("done", GREEN),
}


def colorify(message, color=BLUE):
    """Change color of the standard output.

    Parameters
    ----------
    message : str
        The message to color.

    Returns
    -------
    color_message : str
        The colored message to be displayed in terminal.
    """
    return f"\033[1;{color}m" + message + "\033[0m"


def print_normalize(msg, endline=True, verbose=True):
    """Format the output to have the length of the terminal."""
    if not verbose:
        return

    line_length = max(
        MIN_LINE_LENGTH, shutil.get_terminal_size((100, 24)).columns
    )

    # We add colors to messages using `\033[1;XXm{}\0033[0m`. This adds 11
    # invisible characters for each color we add. Don't take this into
    # account for the line length.
    n_colors = msg.count('\033') // 2
    msg = msg.ljust(line_length + n_colors * 11)

    if endline:
        print(msg)
    else:
        print(msg + '\r', end='', flush=True)


class TerminalOutput:
    def __init__(self, n_repetitions, show_progress):
        # enable ANSI colors in Windows
        if platform.system() == "Windows":
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

        self.n_repetitions = n_repetitions
        self.show_progress = show_progress

        self.solver = None
        self.dataset = None
        self.objective = None

        self.rep = 0
        self.verbose = True

    def clone(self):
        new_output = TerminalOutput(self.n_repetitions, self.show_progress)
        new_output.set(
            solver=self.solver, dataset=self.dataset, objective=self.objective,
            verbose=self.verbose, rep=self.rep
        )
        return new_output

    def set(self, solver=None, dataset=None, objective=None, verbose=None,
            rep=None, i_solver=None):

        if dataset is not None:
            self.dataset = dataset
            self.dataset_tag = f"{dataset}"

        if objective is not None:
            self.objective = objective
            self.objective_tag = f"  |--{objective}"

        if solver is not None:
            self.solver = solver
            self.solver_tag = colorify(f"    |--{solver}:")

        if verbose is not None:
            self.verbose = verbose

        if rep is not None:
            self.rep = rep

        if i_solver is not None:
            self.i_solver = i_solver

    def skip(self, reason=None, objective=False):
        if self.rep == 0 and (not objective or self.i_solver == 0):
            self.show_status(status='skip', objective=objective)
            if reason is not None:
                indent = ' ' * (2 if objective else 4)
                print(f'{indent}Reason: {reason}')

    def savefile_status(self, save_file=None):
        if save_file is None:
            print_normalize(colorify('No output produced.', RED))
        print_normalize(colorify(f'Saving result in: {save_file}', GREEN))

    def _display_name(self, tag):
        assert tag is not None, "Should not happened"
        print_normalize(f"{tag}", verbose=self.verbose)

    def display_dataset(self):
        self._display_name(self.dataset_tag)

    def display_objective(self):
        self._display_name(self.objective_tag)

    def progress(self, progress):
        """Display progress in the CLI interface."""
        if self.show_progress:
            if isinstance(progress, float):
                progress = f'{progress:6.1%}'
            print_normalize(
                f"{self.solver_tag} {progress} "
                f"({self.rep + 1} / {self.n_repetitions} reps)",
                endline=False,  verbose=self.verbose
            )

    def show_status(self, status, dataset=False, objective=False):
        if dataset or objective:
            assert status == 'not installed'
        tag = (
            self.dataset_tag if dataset else
            self.objective_tag if objective else self.solver_tag
        )
        assert status in STATUS, (
            f"status should be in {list(STATUS)}. Got '{status}'"
        )
        status = colorify(*STATUS[status])
        print_normalize(f"{tag} {status}")

    def debug(self, msg):
        if DEBUG:
            print_normalize(f"{self.solver_tag} [DEBUG] - {msg}")
