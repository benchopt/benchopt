"Helper function for colored terminal outputs"
import shutil
import sys
from contextlib import contextmanager
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console

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

    @property
    def key(self):
        return (self.dataset, self.objective, self.solver)

    def stop(self, status):
        self.terminal.stop(self.key, status)

    def skip(self, msg):
        self.terminal.skip(self.key, msg)

    def debug(self, msg):
        self.terminal.debug(msg)

    def start(self):
        self.terminal.init_key(self.key)

    def finish(self):
        self.terminal.increment_key(self.key)


class TerminalOutput:
    def __init__(self, n_repetitions, show_progress=True):
        self.n_repetitions = n_repetitions
        self.show_progress = show_progress
        self.rep = 0
        self.verbose = True

        if show_progress:
            self.progress = Progress(
                TextColumn("[bold blue]{task.fields[dataset]}[/]"),
                TextColumn("|"),
                TextColumn("[cyan]{task.fields[objective]}[/]"),
                TextColumn("|"),
                TextColumn("[green]{task.fields[solver]}[/]"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeRemainingColumn(),
            )
            self.progress.start()
            self.task_ids = {}  # (dataset, objective, solver) -> task_id

    def init_key(self, keys):
        dataset, objective, solver = keys
        if self.show_progress and tuple(keys) not in self.task_ids:
            task_id = self.progress.add_task(
                "",
                total=self.n_repetitions,
                dataset=dataset,
                objective=objective,
                solver=solver,
            )
            self.task_ids[tuple(keys)] = task_id

    def increment_key(self, keys):
        if self.show_progress:
            task_id = self.task_ids.get(keys)
            if task_id is not None:
                self.progress.update(task_id, advance=1)

    def close_progress(self):
        if self.show_progress:
            self.progress.stop()

    def stop(self, key, message):
        dataset, objective, solver = key
        if not self.show_progress:
            return

        task_id = self.task_ids.get(tuple(key))
        if task_id is not None:
            self.progress.remove_task(task_id)

        console.print(
            f"[bold red]❌ {dataset} | {objective} | {solver} "
            f"failed:[/bold red] {message}",
        )

    def skip(self, key, message=None):
        dataset, objective, solver = key
        if not self.show_progress:
            return

        task_id = self.task_ids.get(tuple(key))
        if task_id is not None:
            self.progress.remove_task(task_id)

        error_str = f"🚫 {dataset} | {objective} | {solver} skipped"
        if message is not None:
            error_str += f": {message}"

        console.print(error_str)

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


@contextmanager
def redirect_print(file_path=None):
    if file_path is None:
        yield
        return
    original_stdout = sys.stdout
    with open(file_path, 'w') as f:
        sys.stdout = f
        try:
            yield
        finally:
            sys.stdout = original_stdout
