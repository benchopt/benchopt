"Helper function for colored terminal outputs"
import shutil
import sys
from contextlib import contextmanager
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console
from rich.tree import Tree
from rich.text import Text

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from ..config import DEBUG

console = Console()

MIN_LINE_LENGTH = 20
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)

CROSS = '\u2717'
TICK = '\u2713'


STATUS = {
    'error': ("error", RED),
    'diverged': ("diverged", RED),
    'not installed': ('not installed', RED),
    'interrupted': ("interrupted", YELLOW),
    'not run yet': ('not run yet', YELLOW),
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
        print(msg, file=sys.__stdout__)
    else:
        print(msg + '\r', end='', flush=True, file=sys.__stdout__)


class TerminalLogger:
    def __init__(self, terminal, objective, dataset, solver):
        assert isinstance(terminal, TerminalOutput)
        self.terminal = terminal
        self.objective = objective
        self.dataset = dataset
        self.solver = solver
        self.has_stopped = False

    @property
    def key(self):
        return (self.dataset, self.objective, self.solver)

    def stop(self, status):
        self.has_stopped = True
        self.terminal.stop(self.key, status)

    def skip(self, msg):
        self.has_stopped = True
        self.terminal.skip(self.key, msg)

    def debug(self, msg):
        self.terminal.debug(msg)

    def start(self):
        self.terminal.init_key(self.key)

    def finish(self):
        if not self.has_stopped:
            self.terminal.increment_key(self.key)


class TerminalOutput:
    def __init__(self, n_repetitions, show_progress=True):
        self.n_repetitions = n_repetitions
        self.show_progress = show_progress
        self.rep = 0
        self.verbose = True

        self.structure = {}

    def init_key(self, keys):
        dataset, objective, solver = keys

        # Build nested dict
        if dataset not in self.structure:
            self.structure[dataset] = {}
        if objective not in self.structure[dataset]:
            self.structure[dataset][objective] = {}

        # Add solver task if not present
        if solver not in self.structure[dataset][objective]:
            progress = Progress(
                TextColumn(f"{solver}"),
                BarColumn(),
                TimeRemainingColumn(),
                TextColumn("{task.completed}/{task.total}")
            )
            progress.add_task(
                "", total=self.n_repetitions
            )
            self.structure[dataset][objective][solver] = progress

        if hasattr(self, 'live') and self.show_progress:
            self.live.update(self.render_tree())

    def increment_key(self, keys):
        dataset, objective, solver = keys
        if not self.show_progress:
            return

        if dataset in self.structure:
            if objective in self.structure[dataset]:
                if solver in self.structure[dataset][objective]:
                    self.structure[dataset][objective][solver].advance(0, 1)

    def stop(self, key, message):
        dataset, objective, solver = key
        if not self.show_progress:
            return

        if dataset in self.structure:
            if objective in self.structure[dataset]:
                if solver in self.structure[dataset][objective]:
                    t = Text()
                    t.append(f"❌ {solver} failed", style="bold red")
                    t.append(f" {message}")  # default style
                    self.structure[dataset][objective][solver] = t

    def skip(self, key, message=None):
        dataset, objective, solver = key
        if not self.show_progress:
            return

        if dataset in self.structure:
            if objective in self.structure[dataset]:
                if solver in self.structure[dataset][objective]:
                    self.structure[dataset][objective][solver] = (
                        Text(f"🚫 {solver} skipped")
                    )

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

    def show_status(self, status, dataset=False, objective=False):
        if dataset or objective:
            assert status in ['not installed', 'skip']
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

    def render_tree(self):
        """Render a rich Tree object with the progress bars attached."""
        root = Tree("[bold white]Progress Overview[/]")
        for dataset, objectives in self.structure.items():
            dataset_node = root.add(f"[bold blue]{dataset}[/]")
            for objective, solvers in objectives.items():
                objective_node = dataset_node.add(f"[cyan]{objective}[/]")
                for solver, renderable in solvers.items():
                    # Attach progress bar renderable to solver level
                    objective_node.add(renderable)
        return root


@contextmanager
def redirect_print(file_path=None):
    if file_path is None:
        yield
        return
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    with open(file_path, 'w') as f:
        sys.stdout = f
        sys.stderr = f  # redirect errors too
        try:
            yield
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
