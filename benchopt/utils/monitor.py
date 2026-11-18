"`benchopt monitor`: display the runs from the snapshots they leave behind."
import os
import sys
import json
from time import sleep, time
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

from .rich_output import STALE_AFTER, RichOutput, get_runs_dir, read_jsonl
from .rich_output import SCROLL_HINT, SCROLL_KEYS, _line, _rule
from .rich_output import _ErrorLine


# Keys returned by `click.getchar` for up and down, on POSIX and Windows.
MOVES = {
    '\x1b[A': -1, '\xe0H': -1, '\x00H': -1, 'k': -1,
    '\x1b[B': 1, '\xe0P': 1, '\x00P': 1, 'j': 1,
}
# How often `benchopt monitor --wait` checks if the run is over.
WAIT_PERIOD = 5
STATE_STYLE = {
    'running': 'cyan', 'done': 'green', 'interrupted': 'yellow',
    'error': 'red', 'stale': 'red'
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
    lines, offset = read_jsonl(Path(run['path']).with_suffix(".jsonl"), offset)
    # Skip the `{"finished": ...}` line, the snapshot has it too, and the
    # `{"done": ...}` lines of the workers, counted by the run itself.
    return [line for line in lines if isinstance(line, list)], offset


def load_runs():
    "Snapshots of the last runs, the most recent last, as in a terminal."
    runs = filter(None, map(_load, get_runs_dir().glob("*.json")))
    return sorted(runs, key=lambda run: run['started'])


def run_state(run, now=None):
    """`running`, `done`, `interrupted`, `error`, or `stale` if the run stopped
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
    for column in ["Run", "Benchmark", "State", "Progress", "Duration",
                   "Started"]:
        # The end of the names, e.g. their timestamp, tells the runs apart:
        # wrap them rather than crop them.
        table.add_column(column, overflow="fold")
    now = time()
    for i in range(len(runs)) if rows is None else rows:
        run = runs[i]
        state = run_state(run, now)
        table.add_row(
            escape(run['run_name']), escape(str(run['benchmark'])),
            f"[{STATE_STYLE[state]}]{state}[/]",
            f"{run['n_finished']}/{run['total']}", duration(run, now),
            datetime.fromtimestamp(run['started']).strftime("%Y-%m-%d %H:%M"),
            style="reverse" if i == selected else None,
        )
    return table


def select_run(find_runs, console):
    """Pick a run with the arrow keys, or delete the old ones. None if the
    user quits.

    `find_runs` lists the runs: it is called every second, so that the list
    shows the new runs and their current states.
    """
    from rich.console import Group
    from rich.live import Live
    from rich.markup import escape

    keys = "[dim]↑/↓ select · enter monitor · d delete · q quit[/]"
    runs, i, top, hint = [], 0, 0, keys
    with _read_key() as read, Live(
            console=console, screen=True, auto_refresh=False) as live:
        while True:
            selected = runs[i]['path'] if runs else None
            runs = find_runs()
            if not runs:
                return None
            # Keep the selection on the same run, or on the next one if it
            # is gone. Start on the most recent run, at the bottom.
            paths = [run['path'] for run in runs]
            i = (
                len(runs) - 1 if selected is None
                else paths.index(selected) if selected in paths
                else min(i, len(runs) - 1)
            )
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
                    path = Path(runs[i]['path'])
                    for suffix in [".json", ".jsonl", ".kill"]:
                        path.with_suffix(suffix).unlink(missing_ok=True)
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
        f"{escape(run['run_name'])}"
    )
    if hint is not None:
        view._footer += f" · {hint}"
    # Once the run is over, the log is listed with its outputs.
    if run['log_file'] and 'log' not in (view._outputs or {}):
        view._footer += f" · log: [cyan]{escape(run['log_file'])}[/]"
    return view


def _failed(view):
    "Result lines of the failed runs, carrying their traceback."
    return [line for line in view._lines() if isinstance(line, _ErrorLine)]


class _Pager:
    "Text on the whole screen, scrolled with the keys, e.g. the log."

    def __init__(self, title, text, top=0):
        self.title, self.text, self.top = title, text, top
        self._lines, self._width, self._n = [], None, 1

    def render(self, console):
        from rich.console import Group
        from rich.markup import escape
        from rich.text import Text

        if console.width != self._width:
            self._width = console.width
            # The log holds the colors of the plain output.
            self._lines = list(
                Text.from_ansi(self.text).wrap(console, console.width)
            )
        self._n = n = max(1, console.height - 2)
        self.top = max(0, min(self.top, len(self._lines) - n))
        end = min(self.top + n, len(self._lines))
        return Group(
            _rule(escape(self.title)), *self._lines[self.top:end],
            _line(f"[dim]lines {self.top + 1}-{end} of {len(self._lines)}"
                  f" · esc back{SCROLL_HINT}[/]"),
        )

    def scroll(self, key):
        if key in SCROLL_KEYS:
            direction, unit = SCROLL_KEYS[key]
            step = dict(line=1, page=max(1, self._n - 1),
                        end=len(self._lines))[unit]
            # Clamped on the next render.
            self.top += direction * step


def _has_failed(run):
    "Whether a solver failed, or the run ended otherwise than `done`."
    return run_state(run) not in ('running', 'done') or any(
        run['counts'].get(s) for s in ['error', 'diverged', 'not installed']
    )


def _print_errors(view, run, console):
    "Print the traceback of each failed run, and of the run if it crashed."
    from rich.markup import escape
    from rich.text import Text

    console.print(_rule("Errors"))
    failed = [(line.name, line.traceback) for line in _failed(view)]
    if run.get('traceback'):
        failed.append(("benchopt run", run['traceback']))
    for name, traceback in failed:
        console.print(f"[bold red]{escape(name)}[/]")
        console.print(Text(traceback or "Traceback in the log.\n"))


def follow_run(run, console, wait=False, errors=False):
    """Live display of `run`, until the user quits or asks for its results.

    Without a terminal, or to `wait` for the run to end, its results, or its
    `errors`, are printed. Exit with code 1 if the run failed. Return True if
    the user asked to go back to the list of runs.
    """
    from rich.live import Live

    results, offset = [], 0
    hint = view = pager = selected = None
    updated = 0
    interactive = (
        console.is_terminal and sys.stdin.isatty() and not (wait or errors)
    )

    def update(hint=None):
        nonlocal run, offset, view, updated
        # The file can be gone, e.g. pruned by a new run: keep the last one.
        run = _load(run['path']) or run
        new, offset = read_results(run, offset)
        results.extend(new)
        old = view
        view = _view(run, results, console, hint,
                     progress=view and view._progress)
        # The view is rebuilt from the files: keep where it is scrolled.
        view._scrollable = interactive
        if old is not None:
            view._top, view._window = old._top, old._window
        updated = time()
        return view

    def render():
        if pager is not None:
            return pager.render(console)
        # Redraw often for the spinner, but only read the files every second.
        if view is None or time() - updated > 1:
            keys = " · k kill" if run_state(run) == 'running' else ""
            if run['counts'].get('error') or run.get('traceback'):
                keys += " · e errors"
            if run['log_file']:
                keys += " · l log"
            if selected is not None:
                keys = "[dim]↑/↓ select · enter traceback · esc back[/]"
            else:
                keys = (f"[dim]esc back · q quit · p print results"
                        f"{keys}[/]")
            update(hint or keys)
        view._selected = selected
        return view._render()

    if interactive:
        try:
            with _read_key() as read, Live(
                    get_renderable=render, console=console, screen=True,
                    refresh_per_second=8):
                while True:
                    key = read(1)
                    if pager is not None:
                        if key in ('q', '\x1b'):
                            pager = None
                        elif key is not None:
                            pager.scroll(key)
                        continue
                    if selected is not None:
                        # Picking a failed run, to show its traceback.
                        failed = _failed(view)
                        if key in ('\r', '\n') and failed:
                            line = failed[selected % len(failed)]
                            pager = _Pager(
                                line.name,
                                line.traceback or "Traceback in the log."
                            )
                        elif key in ('\x1b', 'e', 'q'):
                            selected = None
                        elif key in MOVES:
                            selected += MOVES[key]
                        updated = 0
                        continue
                    if key == 'e':
                        if view is not None and _failed(view):
                            selected = 0
                        elif run.get('traceback'):
                            # The run itself crashed.
                            pager = _Pager("benchopt run", run['traceback'])
                        updated = 0
                        continue
                    if key == 'l' and run['log_file']:
                        try:
                            log = Path(run['log_file']).read_text(
                                errors='replace'
                            )
                        except OSError as e:
                            log = f"Could not read the log: {e}"
                        # Start at the end, where the run stopped.
                        pager = _Pager("Log", log, top=len(log))
                        continue
                    if key == 'q':
                        # Detach: the run itself goes on.
                        return
                    if key == '\x1b' and hint is None:
                        # Escape dismisses the hint first, if any.
                        return True
                    if key == 'p':
                        break
                    if view is not None and view.scroll(key):
                        continue
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

    # ponytail: polls the snapshot, a run lasts way more than `WAIT_PERIOD`.
    while wait and run_state(run) == 'running':
        sleep(WAIT_PERIOD)
        run = _load(run['path']) or run
    view = update()
    if errors:
        console.print(view._counters())
        console.print(view._footer)
        _print_errors(view, run, console)
    else:
        view._print_results()
        console.print(view._footer)
        view.show_outputs(**run.get('outputs', {}))
    if _has_failed(run):
        raise SystemExit(1)


def monitor(name=None, wait=False, errors=False):
    """Pick one of the last runs, or the one matching `name`, and follow it.

    `name` is either the start of the run's name or `last` for the most
    recent run. Without a terminal, the matching runs are only listed.
    `wait` and `errors` print the run once it is over, or its errors, for
    scripts and agents: they default to the last run.
    """
    import click
    from rich.console import Console

    def find_runs():
        runs = load_runs()
        if name is None:
            return runs
        if name == 'last':
            return runs[-1:]
        return [run for run in runs if run['run_name'].startswith(name)]

    if (wait or errors) and name is None:
        name = 'last'
    console = Console(highlight=False)
    runs = find_runs()
    if not runs:
        if name is not None:
            raise click.BadParameter(f"No run matching '{name}'.")
        console.print(f"No benchmark run found in {get_runs_dir()}.")
        return

    if len(runs) == 1 and name is not None:
        follow_run(runs[0], console, wait, errors)
        return
    if wait or errors:
        raise click.BadParameter(
            f"'{name}' matches {len(runs)} runs, give more of the name."
        )
    if not sys.stdin.isatty() or not console.is_terminal:
        console.print(runs_table(runs))
        return
    # Escape goes back to the list.
    while True:
        run = select_run(find_runs, console)
        if run is None or not follow_run(run, console):
            return
