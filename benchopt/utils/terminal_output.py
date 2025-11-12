"Helper function for colored terminal outputs"
import shutil
import sys
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.console import Console
from rich.tree import Tree
from rich.text import Text
from rich.markup import escape
import platform
import ctypes

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

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


class TerminalOutput:
    def __init__(self, n_repetitions, show_progress=True):
        self.n_repetitions = n_repetitions
        self.show_progress = show_progress
        self.rep = 0
        self.verbose = True
        self.warnings = {}
        self.structure = {}
        self.init_keys_set = set()

        # TODO: not sure if this is needed anymore
        if platform.system() == "Windows":
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    def update(self, key, msg):
        self.init_key(key)

        if msg == "done":
            msg = None

        self.increment_key(key, msg)

    def init_key(self, key):
        if key in self.init_keys_set:
            return
        self.init_keys_set.add(key)

        # Build nested dict
        dataset, objective, solver = key
        if dataset not in self.structure:
            self.structure[dataset] = {}
        if objective not in self.structure[dataset]:
            self.structure[dataset][objective] = {}

        # Add solver task if not present
        if solver not in self.structure[dataset][objective]:
            progress = Progress(
                TextColumn(f"{solver}", markup=False),
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

    def increment_key(self, key, message=None):
        dataset, objective, solver = key
        if not self.show_progress:
            return

        if message is not None:
            self.warnings[key] = message

        if dataset in self.structure:
            if objective in self.structure[dataset]:
                if solver in self.structure[dataset][objective]:
                    self.structure[dataset][objective][solver].advance(0, 1)
                if self.structure[dataset][objective][solver].finished:
                    t = Text()
                    if key in self.warnings:
                        t.append(
                            f"⚠️  {solver} done, {self.warnings[key]}",
                            style="yellow"
                        )
                    else:
                        t.append(f"✅ {solver} done", style="bold green")
                    self.structure[dataset][objective][solver] = t

    def find_ongoing_runs(self):
        keys = []
        for dataset, objectives in self.structure.items():
            for objective, solvers in objectives.items():
                for solver, progress in solvers.items():
                    if isinstance(progress, Progress):
                        if not progress.finished:
                            keys.append((dataset, objective, solver))
        return keys

    def update_status(self, key, text):
        if not self.show_progress:
            return

        self.init_key(key)
        dataset, objective, solver = key
        self.structure[dataset][objective][solver] = text

    def stop(self, key, message):
        if key is None:
            keys = self.find_ongoing_runs()
            for k in keys:
                self.stop(k, message)
            return

        t = Text()
        t.append(f"❌ {key[3]} failed", style="bold red")
        t.append(f" {message}")  # default style
        self.update_status(key, t)

    def skip(self, key, message):
        t = Text(f"🚫 {key[3]} skipped, {message}")
        self.update_status(key, t)

    def render_tree(self):
        """Render a rich Tree object with the progress bars attached."""
        root = Tree("[bold white]Progress Overview[/]")
        for dataset, objectives in self.structure.items():
            dataset_node = root.add(f"[bold blue]{escape(dataset)}[/]")
            for objective, solvers in objectives.items():
                objective_node = dataset_node.add(
                    f"[cyan]{escape(objective)}[/]"
                )
                for renderable in solvers.values():
                    # Attach progress bar renderable to solver level
                    objective_node.add(renderable)
        return root

    def savefile_status(self, save_file=None):
        if save_file is None:
            print_normalize(colorify('No output produced.', RED))
        print_normalize(colorify(f'Saving result in: {save_file}', GREEN))
