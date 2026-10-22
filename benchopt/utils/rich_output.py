"Live progress display for `benchopt run`, based on `rich`."
import os
import sys
import json
import threading
from time import time
from pathlib import Path
from collections import Counter, defaultdict, deque
from itertools import islice
from contextlib import contextmanager

from .terminal_output import STATUS, TerminalOutput


# Guides for the result tree. The last child of a node is unknown while the
# results stream in, so every entry uses a "more to come" branch.
GUIDE = "[dim]\u2502   [/]"
BRANCH = "[dim]\u251c\u2500\u2500 [/]"

# Asking a scheduler which runs are running spawns a process, so keep it
# way slower than the refresh rate of the display.
PROBE_PERIOD = 30

# The state of the run is dumped in a snapshot for `benchopt monitor`, at most
# every second on progress and every `HEARTBEAT` seconds otherwise. A run whose
# snapshot is not updated for `STALE_AFTER` seconds is considered dead.
HEARTBEAT = 10
STALE_AFTER = 60
# ponytail: fixed retention, make it a config option if anyone asks.
MAX_SNAPSHOTS = 20

# (style, glyph) for each benchopt status. The human readable label is
# reused from `STATUS` in terminal_output.
RICH_STATUS = {
    'error': ("red", "✗"),
    'diverged': ("red", "✗"),
    'not installed': ("red", "✗"),
    'interrupted': ("yellow", "!"),
    'not run yet': ("yellow", "·"),
    'skip': ("yellow", "»"),
    'timeout': ("yellow", "✓"),
    'max_runs': ("yellow", "✓"),
    'done': ("green", "✓"),
}


def _is_cached(status, cached):
    """Whether a result was loaded from the cache instead of being run.

    A run that was skipped has no cached result to speak of, so it is
    reported as a skip.
    """
    from ..runner import SUCCESS_STATUS
    return cached and status in SUCCESS_STATUS


def _guides(level):
    """Tree guides leading to a node at `level`, as in the running section."""
    return GUIDE * (level - 1) + BRANCH if level else ""


def _ellipsis(name, width):
    """Shorten `name` to `width` characters, marking the cut."""
    return name if len(name) <= width else name[:max(width - 3, 0)] + "..."


def _line(markup):
    """A single display line, cropped rather than wrapped.

    Keeping the live display at a fixed number of lines is what makes it
    survive a terminal resize, as `rich` erases the previous frame based on
    the number of lines it printed.
    """
    from rich.text import Text
    text = Text.from_markup(markup, overflow="ellipsis")
    text.no_wrap = True
    return text


def _crop(lines, n, tail=False):
    """Keep `n` lines, reporting how many are left out on an extra one."""
    if len(lines) <= n:
        return lines
    left_out = f"[dim]+{len(lines) - n + 1} more[/]"
    if tail:
        return [left_out] + lines[len(lines) - max(0, n - 1):]
    return lines[:max(0, n - 1)] + [left_out]


def _rule(title):
    """Section separator in the live display."""
    from rich.rule import Rule
    return Rule(f"[bold]{title}[/]", style="dim")


def get_runs_dir():
    "Folder holding the snapshots of the runs, read by `benchopt monitor`."
    from ..config import get_setting
    return Path(os.path.expandvars(get_setting('runs_dir'))).expanduser()


@contextmanager
def _redirect_fds(log_file, mode="w"):
    """Send fd 1 and 2 to `log_file`, yielding a file on the original stdout.

    The redirection is done at the file descriptor level rather than with
    `contextlib.redirect_stdout` so that worker processes, which inherit the
    file descriptors, also write to the log instead of on top of the display.
    """
    sys.stdout.flush()
    sys.stderr.flush()
    tty = os.fdopen(os.dup(1), "w", encoding="utf-8", errors="replace")
    saved_out, saved_err = os.dup(1), os.dup(2)
    log = open(log_file, mode)
    os.dup2(log.fileno(), 1)
    os.dup2(log.fileno(), 2)
    try:
        yield tty
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(saved_out, 1)
        os.dup2(saved_err, 2)
        os.close(saved_out)
        os.close(saved_err)
        log.close()
        tty.close()


class RichOutput(TerminalOutput):
    """Live display of the benchmark progress, in the main process.

    The `terminal` object is pickled to the workers, which cannot share the
    live display. The pickled copy sets `_worker` and falls back to the plain
    `TerminalOutput` behavior, writing to the redirected stdout, i.e. the log
    file.

    Without `display`, e.g. when the output is not a terminal, the main
    process prints the plain output too, but still tracks the state of the
    run so that `benchopt monitor` can display it.
    """

    def __init__(self, n_repetitions=None, show_progress=None, n_jobs=1,
                 display=True):
        super().__init__(n_repetitions, show_progress)
        self._worker = False
        self.display = display
        self.log_file = None
        self.n_jobs = n_jobs

        self.counts = Counter()
        # Dispatched runs that are not finished yet, in dispatch order. Only
        # the first `n_jobs` of them are actually running, the others are
        # waiting for a free worker.
        self.in_flight = deque()
        self.n_configs = None
        # Set by a backend that knows which runs are actually running.
        self._probe = None
        self._probe_keys, self._probe_time = [], 0
        self._probe_lock = threading.Lock()
        # Result tree: dataset -> objective -> lines of its finished runs,
        # in the order they first appeared.
        self._tree = {}
        self._labels = {}
        self.n_dispatched = 0
        self.n_finished = 0
        self._all_dispatched = False

        self.console = None
        self._tty_fd = None
        self._width = None
        self._live = None
        self._progress = None
        self._task = None
        # Line added below the counters, used by `benchopt monitor`.
        self._footer = None

        self._meta = {}
        self._snapshot_file = None
        self._dump_time = 0
        self._dump_lock = threading.Lock()

    def __getstate__(self):
        state = self.__dict__.copy()
        for k in ['console', '_tty_fd', '_live', '_progress', '_task',
                  '_probe', '_probe_lock', '_snapshot_file', '_dump_lock']:
            state[k] = None
        state['_worker'] = True
        state['display'] = False
        # With the display, the progress of the workers would only clutter
        # the log. Without it, they print it as the plain output does.
        state['show_progress'] = self.show_progress and not self.display
        return state

    # Display life cycle ####################################################

    @contextmanager
    def live(self, log_file=None, benchmark=None):
        if self.display:
            self.log_file = log_file
        self._start_snapshot(log_file, benchmark)

        # Keep the snapshot fresh, and the scheduler probed, while no run
        # finishes: `benchopt monitor` tells a long run from a dead one.
        stop = threading.Event()

        def heartbeat():
            while not stop.wait(HEARTBEAT):
                self._dump()

        threading.Thread(target=heartbeat, daemon=True).start()
        finished = 'interrupted'
        try:
            if self.display:
                with self._live_display(log_file):
                    yield
            else:
                yield
            finished = 'done'
        finally:
            stop.set()
            self._meta['finished'] = finished
            self._dump()

    def _make_progress(self, started=None, stopped=None):
        """Progress bar of the runs, timed from `started` if given."""
        from rich.progress import (
            BarColumn, MofNCompleteColumn, Progress, SpinnerColumn,
            TextColumn, TimeElapsedColumn
        )
        # Wall clock time, so that `benchopt monitor` can time the bar from
        # the start of the run, in another process.
        self._progress = Progress(
            SpinnerColumn(), TextColumn("[bold]Runs"), BarColumn(),
            MofNCompleteColumn(), TimeElapsedColumn(),
            console=self.console, get_time=time,
        )
        self._task = self._progress.add_task("runs", total=None)
        task = self._progress.tasks[0]
        if started is not None:
            task.start_time = started
        task.stop_time = stopped

    @contextmanager
    def _live_display(self, log_file):
        from rich.console import Console
        from rich.live import Live

        try:
            with _redirect_fds(log_file) as tty:
                self._tty_fd = tty.fileno()
                self.console = Console(file=tty, highlight=False)
                self._make_progress()
                try:
                    # The display runs on the alternate screen, so that the
                    # terminal redraws it on a resize and the output of the
                    # run is left untouched. `redirect_stdout` would re-print
                    # the main process output on the console: everything goes
                    # to the log instead.
                    with Live(get_renderable=self._render,
                              console=self.console, screen=True,
                              refresh_per_second=8, redirect_stdout=False,
                              redirect_stderr=False) as live:
                        self._live = live
                        yield
                finally:
                    self._live = None
                    # The alternate screen is gone: print the results, that
                    # were only visible in the display, on the terminal.
                    self._print_results()
        finally:
            # The file descriptors are restored: keep a console on the real
            # stdout so that trailing output, e.g. an interrupted status,
            # stays in the same style.
            self.console = Console(highlight=False)

    @contextmanager
    def step(self, label):
        """Run a post-run step under a spinner, its output going to the log."""
        if not self.display or self.log_file is None:
            yield
            return

        from rich.console import Console
        from rich.live import Live
        from rich.spinner import Spinner

        with _redirect_fds(self.log_file, mode="a") as tty:
            console = Console(file=tty, highlight=False)
            # `console.status` would capture stdout and print it on the
            # console: the output of the step goes to the log instead.
            with Live(Spinner("dots", f"[bold]{label}[/]"), console=console,
                      refresh_per_second=8, redirect_stdout=False,
                      redirect_stderr=False, transient=True):
                yield
            console.print(f"[green]\u2713[/] {label}")

    def show_outputs(self, **files):
        """Report where the outputs of the run are available."""
        files = {k: v for k, v in files.items() if v is not None}
        if self.log_file is None:
            # Without the display, the output went to stdout, not to a log.
            files.pop('log', None)
        if not self._worker:
            self._meta['outputs'] = {k: str(v) for k, v in files.items()}
            self._dump()
        if not self.display or self.console is None or not files:
            return
        self.console.print(_rule("Outputs"))
        width = max(len(name) for name in files)
        for name, path in files.items():
            self.console.print(
                f"[bold]{name:{width}}[/]  [cyan]{path}[/]"
            )

    def _render(self):
        from rich.console import Group

        # `rich` looks up the size on fd 0, 1 and 2, which are redirected, so
        # read it on the terminal itself to follow a resize.
        try:
            # A pseudo-terminal can report 0, which would render nothing.
            size = os.get_terminal_size(self._tty_fd)
            if size.columns and size.lines:
                self.console.size = size
                if size.columns != self._width:
                    # The frames are drawn from the top of the screen: on a
                    # resize, wipe what is left of the previous ones. The
                    # first frame is skipped, as the alternate screen is not
                    # up yet and clearing scrolls the terminal.
                    first, self._width = self._width is None, size.columns
                    if not first:
                        self.console.clear()
        except (OSError, TypeError):
            pass

        totals = [_rule("Total")]
        if self._progress is not None:
            totals.append(self._progress)
        totals.append(_line(self._counters()))
        if self._footer is not None:
            totals.append(_line(self._footer))

        # The screen does not scroll, so the sections share what is left
        # once the two titles and the totals, which always fit, are placed.
        # The results are all printed on the terminal once the run is over.
        results = list(self._lines())
        free = max(0, self.console.height - len(totals) - 2)
        # The runs in flight get half of the space when the results fill it.
        # With a scheduler, thousands of runs can be in flight, so the lines
        # that do not fit are not built at all.
        running = self._running_lines(max(free - len(results), free // 2))
        results = _crop(results, free - len(running), tail=True)

        return Group(_rule("Results"), *map(_line, results),
                     _rule("Running"), *map(_line, running), *totals)

    def _running_lines(self, max_lines=None):
        """One line per dataset, objective and solver of the runs in flight."""
        from rich.markup import escape
        from rich.text import Text

        running = Counter(self._running_keys())
        if not running:
            return ["[dim]waiting for runs...[/]"]

        # Group the runs by dataset and objective, as their names are long
        # and shared by several solvers.
        lines, seen, n_shown = [], set(), 0
        for key, n in sorted(running.items()):
            # A run adds up to 3 lines, plus the one counting the hidden
            # ones: stop early rather than let `_crop` miscount them.
            if max_lines is not None and len(lines) + 4 > max_lines:
                break
            n_shown += n
            data, obj, solver = key
            for level, node in enumerate([(data,), (data, obj)]):
                if node not in seen:
                    seen.add(node)
                    lines.append(
                        f"{_guides(level)}[bold]{escape(node[-1])}[/]"
                    )
            reps = f"{n} reps" if n > 1 else "1 rep"
            suffix = (f" \u2014 [magenta]{reps}[/] running "
                      f"({self.rep[key]}/{self.n_repetitions} done)")
            # A solver with many parameters would push the counters out of
            # the line, so it is the name that gets cropped instead.
            width = self.console.width - 8 - len(Text.from_markup(suffix))
            lines.append(
                f"{_guides(2)}[cyan]{escape(_ellipsis(solver, width))}[/]"
                f"{suffix}"
            )

        n_hidden = len(self.in_flight) - n_shown
        if n_hidden > 0:
            # The hidden runs are queued ones, plus the ones left out above.
            label = "queued" if n_shown == sum(running.values()) else "more"
            lines.append(f"[dim]+{n_hidden} {label}[/]")
        return lines

    def _running_keys(self):
        """The runs holding a worker, as told by the backend or guessed."""
        with self._probe_lock:
            if self._probe is not None and time() - self._probe_time > (
                    PROBE_PERIOD):
                self._probe_time = time()
                try:
                    self._probe_keys = list(self._probe())
                except Exception:
                    # The display is never worth taking the run down for.
                    self._probe = None
            if self._probe is not None:
                return self._probe_keys

        # Without a probe, the runs are dispatched in order, so the oldest
        # unfinished ones are the ones actually holding a worker.
        return list(islice(self.in_flight, self.n_jobs))

    def _lines(self):
        """The whole result tree, as one markup line per node."""
        from rich.markup import escape

        for data, objectives in self._tree.items():
            yield from self._labels.get(
                (data,), [f"[bold]{escape(data)}[/]"]
            )
            for obj, lines in objectives.items():
                yield from self._labels.get(
                    (data, obj), [f"{_guides(1)}[bold]{escape(obj)}[/]"]
                )
                yield from lines

    def _print_results(self):
        """Print the whole result tree, once the display is over."""
        self.console.print(_rule("Results"))
        for markup in self._lines():
            self._print(markup)
        self._print(self._counters())

    def _print(self, markup):
        """Print one result line, wrapped under the name of the run."""
        from rich.text import Text

        text = Text.from_markup(markup)
        # Long names, e.g. a solver with many parameters, have to wrap: keep
        # the tree readable by indenting past the guides and the status glyph.
        plain = text.plain
        level = (len(plain) - len(plain.lstrip("│├─ "))) // 4
        indent = min(4 * level + 2, max(self.console.width - 8, 0))
        lines = text[indent:].wrap(self.console, self.console.width - indent)
        # The wrapped lines carry on the guides of the nodes above them.
        pad = Text.from_markup(GUIDE * level + "  ")
        self.console.print(Text("\n").join(
            [text[:indent] + line for line in lines[:1]]
            + [pad + line for line in lines[1:]]
        ))

    def _total(self):
        """Number of runs to display in the progress bar.

        `n_configs` is only an upper bound, as some runs are skipped, so
        fall back on the exact count once everything has been dispatched.
        """
        if self._all_dispatched or self.n_configs is None:
            return self.n_dispatched
        return max(self.n_configs * (self.n_repetitions or 1),
                   self.n_dispatched)

    def _counters(self):
        done = sum(self.counts[s] for s in ['done', 'timeout', 'max_runs'])
        errors = sum(
            self.counts[s] for s in ['error', 'diverged', 'not installed']
        )
        return (
            f"[green]done {done}[/] · [cyan]cached "
            f"{self.counts['cached']}[/] · [yellow]skip "
            f"{self.counts['skip']}[/] · [red]error {errors}[/]"
        )

    # TerminalOutput interface ##############################################

    def show_interrupted(self):
        # Nothing to report: the interrupted runs produced no result, and
        # they are already accounted for in the progress bar.
        if not self.display:
            super().show_interrupted()

    def start_run(self, meta):
        if self._worker:
            return
        key = (
            meta['dataset_name'], meta['objective_name'], meta['solver_name']
        )
        self.in_flight.append(key)
        self.n_dispatched += 1
        self._refresh()

    def set_n_configs(self, n_configs):
        self.n_configs = n_configs
        self._refresh()

    def all_dispatched(self):
        self._all_dispatched = True
        self._refresh()

    def set_running_probe(self, probe):
        """Register a callable listing the runs that are actually running.

        A scheduler, e.g. SLURM, knows which of the dispatched runs left the
        queue. Without a probe, the oldest dispatched ones are assumed to be
        the running ones.
        """
        if not self._worker:
            self._probe, self._probe_time = probe, 0

    def show_status(self, status, reason=None, dataset=False, objective=False,
                    cached=False):
        if self._worker:
            return super().show_status(status, reason, dataset, objective,
                                       cached)

        if not (dataset or objective):
            key = (str(self.dataset), str(self.objective), str(self.solver))
            self.n_finished += 1
            bucket = 'cached' if _is_cached(status, cached) else status
            self.counts[bucket] += 1
            if key in self.in_flight:
                self.in_flight.remove(key)

        super().show_status(status, reason, dataset, objective, cached)
        self._refresh()

    def _emit_status(self, status, reason, dataset, objective, cached):
        if not self.display:
            super()._emit_status(status, reason, dataset, objective, cached)
        if self._worker:
            return

        from rich.markup import escape

        if _is_cached(status, cached):
            style, glyph = RICH_STATUS['done']
            result = "[green]done[/] [cyan](cached)[/]"
        else:
            style, glyph = RICH_STATUS[status]
            result = f"[{style}]{STATUS[status][0]}[/]"
            if status in ['error', 'diverged']:
                result += " [dim](traceback in the log)[/]"

        level = 0 if dataset else 1 if objective else 2
        name = str([self.dataset, self.objective, self.solver][level])
        lines = [
            f"{_guides(level)}[{style}]{glyph}[/] {escape(name)} {result}"
        ]
        if status == 'skip' and reason is not None:
            lines.append(
                f"{GUIDE * level}[dim]Reason: {escape(str(reason))}[/]"
            )

        data, obj = str(self.dataset), str(self.objective)
        objectives = self._tree.setdefault(data, {})
        if level == 0:
            self._labels[data, ] = lines
        elif level == 1:
            objectives.setdefault(obj, [])
            self._labels[data, obj] = lines
        else:
            objectives.setdefault(obj, []).extend(lines)

    def _refresh(self):
        if self._progress is not None:
            self._progress.update(
                self._task, completed=self.n_finished, total=self._total()
            )
        if self._live is not None:
            self._live.refresh()
        if time() - self._dump_time > 1:
            self._dump()

    # In the main process, these are subsumed by the live display. In the
    # workers or without display, they keep printing.
    def progress(self, progress, key):
        if not self.display:
            super().progress(progress, key)

    def debug(self, msg):
        if not self.display:
            super().debug(msg)

    def display_dataset(self):
        if not self.display:
            super().display_dataset()

    def display_objective(self):
        if not self.display:
            super().display_objective()

    # Snapshots for `benchopt monitor` ######################################

    def _start_snapshot(self, log_file, benchmark):
        """Create the snapshot file of this run, pruning the oldest ones."""
        if self._worker:
            return
        run_name = Path(log_file).stem if log_file else "benchopt_run"
        self._meta = dict(
            run_name=run_name, benchmark=benchmark, pid=os.getpid(),
            log_file=str(log_file) if self.log_file else None,
            started=time(), finished=None,
        )
        try:
            runs_dir = get_runs_dir()
            runs_dir.mkdir(parents=True, exist_ok=True)
            old = sorted(runs_dir.glob("*.json"), key=os.path.getmtime)
            for f in old[:max(0, len(old) - MAX_SNAPSHOTS + 1)]:
                f.unlink(missing_ok=True)
            self._snapshot_file = runs_dir / f"{run_name}-{os.getpid()}.json"
        except OSError:
            self._snapshot_file = None
        self._dump()

    def _snapshot(self):
        """State of the run needed by `_render`, as a JSON-able dict."""
        return dict(
            self._meta, updated=time(), total=self._total(),
            n_repetitions=self.n_repetitions, n_jobs=self.n_jobs,
            n_configs=self.n_configs, n_dispatched=self.n_dispatched,
            n_finished=self.n_finished, all_dispatched=self._all_dispatched,
            counts=self.counts, in_flight=list(self.in_flight),
            running=self._running_keys(),
            rep=[[list(map(str, k)), n] for k, n in self.rep.items()],
            tree=self._tree,
            labels=[[list(k), lines] for k, lines in self._labels.items()],
        )

    def _dump(self):
        if self._worker or self._snapshot_file is None:
            return
        with self._dump_lock:
            self._dump_time = time()
            tmp = self._snapshot_file.with_suffix(".tmp")
            try:
                tmp.write_text(json.dumps(self._snapshot()))
                # Atomic, so that `benchopt monitor` never reads half a file.
                os.replace(tmp, self._snapshot_file)
            except Exception:
                # Monitoring is never worth taking the run down for, e.g. on
                # a full disk. A state changed mid-dump is fixed by the next.
                pass

    @classmethod
    def from_snapshot(cls, snapshot, console, stopped=None):
        """Rebuild the display of a run from its snapshot.

        `stopped` is the time the run stopped at, if it is over.
        """
        self = cls(snapshot['n_repetitions'], False,
                   n_jobs=snapshot['n_jobs'])
        self._meta = snapshot
        self.log_file = snapshot['log_file']
        self.console = console
        self.n_configs = snapshot['n_configs']
        self.n_dispatched = snapshot['n_dispatched']
        self.n_finished = snapshot['n_finished']
        self._all_dispatched = snapshot['all_dispatched']
        self.counts = Counter(snapshot['counts'])
        self.in_flight = deque(map(tuple, snapshot['in_flight']))
        running = list(map(tuple, snapshot['running']))
        # The run already probed the scheduler: use its answer as is.
        self._running_keys = lambda: running
        self.rep = defaultdict(
            int, {tuple(k): n for k, n in snapshot['rep']}
        )
        self._tree = snapshot['tree']
        self._labels = {tuple(k): lines for k, lines in snapshot['labels']}
        self._make_progress(started=snapshot['started'], stopped=stopped)
        self._refresh()
        return self


def make_terminal_output(n_repetitions=None, show_progress=None, pdb=False,
                         n_jobs=1):
    """Rich live display if running in an interactive terminal, plain else.

    The state of the run is tracked in both cases, for `benchopt monitor`.
    """
    from ..config import get_setting
    display = not (pdb or get_setting('no_rich') or not sys.stdout.isatty())
    return RichOutput(n_repetitions, show_progress, n_jobs=n_jobs,
                      display=display)
