"`benchopt monitor`: display the runs from the snapshots they leave behind."
import os
import sys
import json
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
        return dict(json.loads(Path(path).read_text()), path=str(path))
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


def runs_table(runs, selected=None, rows=None):
    "Table of the `runs`, or of the ones whose index is in `rows`."
    from rich.markup import escape
    from rich.table import Table

    table = Table(box=None, header_style="bold")
    for column in ["#", "Run", "Benchmark", "State", "Progress", "Duration",
                   "Started"]:
        # The end of the names, e.g. their timestamp, tells the runs apart:
        # wrap them rather than crop them.
        table.add_column(column, overflow="fold")
    now = time()
    for i in range(len(runs)) if rows is None else rows:
        run = runs[i]
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
    """Pick a run with the arrow keys, or delete the old ones. None if the
    user quits."""
    from rich.console import Group
    from rich.live import Live
    from rich.markup import escape

    keys = "[dim]↑/↓ select · enter monitor · d delete · q quit[/]"
    i, top, hint = 0, 0, keys
    with _read_key() as read, Live(
            console=console, screen=True, auto_refresh=False) as live:
        while runs:
            # Re-read every second, so that the states stay current.
            runs = [_load(run['path']) or run for run in runs]
            # Scroll to keep the selected run on screen, below the header.
            # ponytail: one line per run, a name folded on a narrow terminal
            # can push the selection off screen.
            n_rows = max(1, console.height - 2)
            top = min(max(top, i - n_rows + 1), i)
            rows = range(top, min(top + n_rows, len(runs)))
            live.update(Group(runs_table(runs, i, rows), hint), refresh=True)
            key = read(1)
            if key is None:
                continue
            if hint.startswith("[red]Delete"):
                if key == 'y':
                    path = Path(runs.pop(i)['path'])
                    for suffix in [".json", ".jsonl", ".kill"]:
                        path.with_suffix(suffix).unlink(missing_ok=True)
                    i = max(0, min(i, len(runs) - 1))
                hint = keys
            elif key in ('\r', '\n'):
                return runs[i]
            elif key in ('q', '\x1b'):
                return None
            elif key == 'd':
                hint = (
                    "[red]Kill the run before deleting it.[/]"
                    if run_state(runs[i]) == 'running' else
                    f"[red]Delete {escape(runs[i]['run_name'])}? "
                    "y to confirm[/]"
                )
            else:
                i = (i + MOVES.get(key, 0)) % len(runs)
                hint = keys


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
                    key = msvcrt.getwch()
                    # Arrows come as two characters, e.g. '\xe0H'.
                    if key in ('\x00', '\xe0'):
                        key += msvcrt.getwch()
                    return key
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

    The run polls for this request, so it works from any machine sharing the
    runs folder, e.g. another node of a cluster. The run saves its results
    and stops, cancelling its SLURM jobs if any.
    """
    try:
        Path(run['path']).with_suffix(".kill").touch()
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
        f"[bold {STATE_STYLE[state]}]{state}[/] · "
        f"{escape(run['run_name'])} · {duration(run)}"
    )
    if hint is not None:
        view._footer += f" · {hint}"
    # Once the run is over, the log is listed with its outputs.
    if run['log_file'] and 'log' not in (view._outputs or {}):
        view._footer += f" · log: [cyan]{escape(run['log_file'])}[/]"
    return view


def follow_run(run, console):
    """Live display of `run`, until the user quits or asks for its results.

    Without a terminal, its results are printed right away.
    """
    from rich.live import Live

    results, offset = [], 0
    hint = view = None
    updated = 0

    def update(hint=None):
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
            kill = " · k kill" if run_state(run) == 'running' else ""
            update(hint or f"[dim]q quit · p print results{kill}[/]")
        return view._render()

    if console.is_terminal and sys.stdin.isatty():
        try:
            with _read_key() as read, Live(
                    get_renderable=render, console=console, screen=True,
                    refresh_per_second=8):
                while True:
                    key = read(1)
                    if key == 'q':
                        # Detach: the run itself goes on.
                        return
                    if key == 'p':
                        break
                    if hint is not None:
                        # Confirming a kill, or showing its outcome.
                        if key == 'y' and hint.startswith("[red]Kill"):
                            hint = kill_run(run)
                        elif key is not None:
                            hint = None
                    elif key == 'k' and run_state(run) == 'running':
                        hint = "[red]Kill the run? y to confirm[/]"
                    if key is not None:
                        # Show the new hint right away.
                        updated = 0
        except KeyboardInterrupt:
            pass

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
