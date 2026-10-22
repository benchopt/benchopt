"`benchopt monitor`: display the runs from the snapshots they leave behind."
import os
import sys
import json
import signal
import socket
from time import sleep, time
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

from .rich_output import STALE_AFTER, RichOutput, get_runs_dir


# Keys returned by `click.getchar` for up and down, on POSIX and Windows.
MOVES = {
    '\x1b[A': -1, '\xe0H': -1, '\x00H': -1, 'k': -1,
    '\x1b[B': 1, '\xe0P': 1, '\x00P': 1, 'j': 1,
}
STATE_STYLE = {
    'running': 'cyan', 'done': 'green', 'interrupted': 'yellow', 'stale': 'red'
}


def _load(path):
    "Snapshot stored in `path`, None if it is gone or unreadable."
    try:
        return dict(json.loads(open(path).read()), path=str(path))
    except (OSError, ValueError):
        return None


def read_results(run, offset=0):
    """Results of `run` written past `offset`, and the offset to read from
    next time, so that following a run only reads the new results."""
    try:
        with open(Path(run['path']).with_suffix(".jsonl"), "rb") as f:
            f.seek(offset)
            data = f.read()
    except OSError:
        return [], offset
    # The last line can be partly written: leave it for the next read.
    data = data[:data.rfind(b"\n") + 1]
    return [json.loads(line) for line in data.splitlines()], offset + len(data)


def load_runs():
    "Snapshots of the last runs, the most recent first."
    runs = filter(None, map(_load, get_runs_dir().glob("*.json")))
    return sorted(runs, key=lambda run: run['started'], reverse=True)


def run_state(run, now=None):
    """`running`, `done`, `interrupted`, or `stale` if the run stopped
    updating its snapshot without finishing, e.g. it was killed."""
    if run['finished']:
        return run['finished']
    now = time() if now is None else now
    return 'stale' if now - run['updated'] > STALE_AFTER else 'running'


def duration(run, now=None):
    "For how long the run has been running, or ran."
    now = time() if now is None else now
    end = now if run_state(run, now) == 'running' else run['updated']
    minutes, seconds = divmod(int(end - run['started']), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"
    return f"{minutes}m {seconds:02d}s" if minutes else f"{seconds}s"


def runs_table(runs, selected=None):
    from rich.markup import escape
    from rich.table import Table

    table = Table(box=None, header_style="bold")
    for column in ["#", "Run", "Benchmark", "State", "Progress", "Duration",
                   "Started"]:
        # The end of the names, e.g. their timestamp, tells the runs apart:
        # wrap them rather than crop them.
        table.add_column(column, overflow="fold")
    now = time()
    for i, run in enumerate(runs):
        state = run_state(run, now)
        table.add_row(
            str(i + 1), escape(run['run_name']), escape(str(run['benchmark'])),
            f"[{STATE_STYLE[state]}]{state}[/]",
            f"{run['n_finished']}/{run['total']}", duration(run, now),
            datetime.fromtimestamp(run['started']).strftime("%Y-%m-%d %H:%M"),
            style="reverse" if i == selected else None,
        )
    return table


def select_run(runs, console):
    "Pick a run with the arrow keys. None if the user quits."
    import click
    from rich.console import Group
    from rich.live import Live

    i = 0
    with Live(console=console, transient=True, auto_refresh=False) as live:
        while True:
            # Re-read on each key press, so that the states stay current.
            runs = [_load(run['path']) or run for run in runs]
            live.update(Group(
                runs_table(runs, selected=i),
                "[dim]↑/↓ select · enter monitor · q quit[/]",
            ), refresh=True)
            key = click.getchar()
            if key in ('\r', '\n'):
                return runs[i]
            if key in ('q', '\x1b'):
                return None
            i = (i + MOVES.get(key, 0)) % len(runs)


@contextmanager
def _read_key():
    """Yield a `read(timeout)` returning the key pressed, or None.

    Unlike `click.getchar`, the terminal is not put in raw mode, which would
    garble the live display, and the keys are read with a timeout.
    """
    if sys.platform == 'win32':
        import msvcrt

        def read(timeout):
            end = time() + timeout
            while time() < end:
                if msvcrt.kbhit():
                    return msvcrt.getwch()
                sleep(0.05)
        yield read
        return

    import termios
    import tty
    from select import select

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        # Keys are read one by one, without echo, Ctrl-C still interrupts.
        tty.setcbreak(fd)
        yield lambda timeout: (
            os.read(fd, 32).decode(errors='replace')
            if select([fd], [], [], timeout)[0] else None
        )
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def kill_run(run):
    """Interrupt `run` as Ctrl-C would. Return a message telling the outcome.

    The run saves its results and stops, cancelling its SLURM jobs if any.
    """
    host = run.get('host')
    if host != socket.gethostname():
        return f"[red]The run is on {host}: kill it from there.[/]"
    try:
        # ponytail: on Windows, os.kill terminates the process, without
        # saving the results: the run shows as stale.
        os.kill(run['pid'], signal.SIGINT)
    except OSError as e:
        return f"[red]Could not kill the run: {e}[/]"
    return "[yellow]Interrupting the run...[/]"


def _view(run, results, console, hint=None, progress=None):
    "Display of `run`, as `benchopt run` shows it, with its state below."
    from rich.markup import escape

    state = run_state(run)
    view = RichOutput.from_snapshot(
        run, results, console, progress=progress,
        stopped=None if state == 'running' else run['updated']
    )
    view._footer = (
        f"[bold]{escape(run['run_name'])}[/] · "
        f"[{STATE_STYLE[state]}]{state}[/] · {duration(run)}"
    )
    if hint is not None:
        view._footer += f" · {hint}"
    if run['log_file']:
        view._footer += f" · log: [cyan]{escape(run['log_file'])}[/]"
    return view


def follow_run(run, console):
    """Live display of `run` until it stops, then print its results."""
    from rich.live import Live

    results, offset = [], 0
    keys = "[dim]q quit · k kill[/]"
    hint = view = None
    updated = 0

    def update():
        nonlocal run, offset, view, updated
        # The file can be gone, e.g. pruned by a new run: keep the last one.
        run = _load(run['path']) or run
        new, offset = read_results(run, offset)
        results.extend(new)
        view = _view(run, results, console, hint,
                     progress=view and view._progress)
        updated = time()
        return view

    def render():
        # Redraw often for the spinner, but only read the files every second.
        if view is None or time() - updated > 1:
            update()
        return view._render()

    if console.is_terminal and run_state(run) == 'running':
        hint = keys
        try:
            with _read_key() as read, Live(
                    get_renderable=render, console=console, screen=True,
                    refresh_per_second=8):
                while run_state(run) == 'running':
                    key = read(1)
                    if key == 'q':
                        # Detach: the run itself goes on.
                        break
                    if hint.startswith("[red]Kill"):
                        if key == 'y':
                            hint = kill_run(run)
                        elif key is not None:
                            hint = keys
                    elif key == 'k':
                        hint = "[red]Kill the run? y to confirm[/]"
                    if key is not None:
                        # Show the new hint right away.
                        updated = 0
        except KeyboardInterrupt:
            pass
        hint = None

    view = update()
    view._print_results()
    console.print(view._footer)
    view.show_outputs(**run.get('outputs', {}))


def monitor(name=None):
    """Pick one of the last runs, or the one matching `name`, and follow it.

    `name` is either the number of the run in the table or the start of its
    name. Without a terminal, the matching runs are only listed.
    """
    import click
    from rich.console import Console

    console = Console(highlight=False)
    runs = load_runs()
    if name is not None:
        if name.isdigit() and 1 <= int(name) <= len(runs):
            runs = [runs[int(name) - 1]]
        else:
            runs = [run for run in runs if run['run_name'].startswith(name)]
        if not runs:
            raise click.BadParameter(f"No run matching '{name}'.")
    if not runs:
        console.print(f"No benchmark run found in {get_runs_dir()}.")
        return

    if len(runs) > 1 or name is None:
        if not sys.stdin.isatty() or not console.is_terminal:
            console.print(runs_table(runs))
            return
        run = select_run(runs, console)
        if run is None:
            return
    else:
        run = runs[0]
    follow_run(run, console)
