import io
import os
import pickle
import sys

from rich.console import Console

from benchopt.utils.terminal_output import TerminalOutput
from benchopt.utils.rich_output import RichOutput, _redirect_fds
from benchopt.utils.rich_output import make_terminal_output


META = dict(
    # Names contain brackets, which are `rich` markup and must be escaped.
    dataset_name="simu[n_samples=10]",
    objective_name="obj[reg=0.1]",
    solver_name="solver[lr=1e-3]",
)
KEY = tuple(META.values())


def _render_to_str(terminal):
    "Render the live display in a string, without any terminal involved."
    from rich.console import Console

    console = Console(file=io.StringIO(), width=120, highlight=False)
    console.print(terminal._render())
    return console.file.getvalue()


def test_redirect_fds(tmp_path):
    log_file = tmp_path / "run.log"
    # Write on the file descriptors rather than with `print`, as pytest
    # replaces `sys.stdout` with an object that does not use fd 1.
    with _redirect_fds(log_file):
        os.write(1, b"from this process\n")
        os.system("echo from subprocess")

    log = log_file.read_text()
    assert "from this process" in log
    assert "from subprocess" in log

    # The file descriptors are restored on exit.
    os.system("echo back on stdout")
    assert "back on stdout" not in log_file.read_text()


def test_rich_output(tmp_path):
    log_file = tmp_path / "run.log"
    terminal = RichOutput(n_repetitions=2, show_progress=False, n_jobs=2)
    terminal.set_n_configs(3)

    with terminal.live(log_file=log_file):
        terminal.set(dataset=KEY[0], objective=KEY[1], solver=KEY[2])

        # Two repetitions of the same run are stacked on a single line.
        terminal.start_run(META)
        terminal.start_run(META)
        assert terminal.n_dispatched == 2
        assert terminal._total() == 6

        # The runs are displayed as a dataset > objective > solver tree.
        display = _render_to_str(terminal)
        assert display.count("simu[n_samples=10]") == 1
        assert "Running" in display and "Total" in display
        assert "solver[lr=1e-3] — 2 reps running (0/2 done)" in display

        # Only `n_jobs` runs hold a worker, the ones dispatched after wait.
        terminal.start_run(META)
        display = _render_to_str(terminal)
        assert "2 reps running" in display
        assert "+1 queued" in display

        # In the workers, the display falls back to the plain output.
        worker_terminal = pickle.loads(pickle.dumps(terminal))
        assert worker_terminal._worker
        assert worker_terminal.console is None

        for _ in range(3):
            terminal.show_status(status='done')
        assert len(terminal.in_flight) == 0
        assert terminal.n_finished == 3
        assert terminal.counts['done'] == 3

        # Once everything is dispatched, the total is exact.
        terminal.all_dispatched()
        assert terminal._total() == 3

        os.system("echo output of the run")

    assert "output of the run" in log_file.read_text()


def test_rich_output_result_tree():
    from rich.console import Console

    terminal = RichOutput(n_repetitions=1, show_progress=False)
    terminal.console = Console(file=io.StringIO(), width=120,
                               highlight=False)

    runs = [
        ("data[n=1]", "obj[p=1]", "s1", 'done', False),
        ("data[n=1]", "obj[p=1]", "s2", 'max_runs', True),
        ("data[n=1]", "obj[p=2]", "s1", 'error', False),
        ("data[n=2]", "obj[p=1]", "s1", 'skip', True),
    ]
    for data, obj, solver, status, cached in runs:
        terminal.set(dataset=data, objective=obj, solver=solver)
        terminal.show_status(status=status, cached=cached, reason="a reason")
    terminal.show_status(status='interrupted')

    # The results are only printed once the display is over.
    assert terminal.console.file.getvalue() == ""
    for markup in terminal._lines():
        terminal.console.print(markup)
    display = terminal.console.file.getvalue()
    assert display == (
        "data[n=1]\n"
        "├── obj[p=1]\n"
        "│   ├── ✓ s1 done\n"
        # A cached result is reported as done, whatever stopped the run.
        "│   ├── ✓ s2 done (cached)\n"
        "├── obj[p=2]\n"
        "│   ├── ✗ s1 error (traceback in the log)\n"
        "data[n=2]\n"
        "├── obj[p=1]\n"
        # A skipped run has no cached result to report.
        "│   ├── » s1 skip\n"
        "│   │   Reason: a reason\n"
        # A run interrupted mid-way is reported as any other status.
        "│   ├── ! s1 interrupted\n"
    )
    assert terminal.counts == {
        'done': 1, 'cached': 1, 'error': 1, 'skip': 1, 'interrupted': 1
    }


def test_rich_output_interrupted():
    from rich.console import Console

    terminal = RichOutput(n_repetitions=1, show_progress=False, n_jobs=2)
    terminal.console = Console(file=io.StringIO(), width=120,
                               highlight=False)

    terminal.start_run(META)
    terminal.set(dataset=KEY[0], objective=KEY[1], solver=KEY[2])
    terminal.show_status(status='done')

    # A keyboard interruption does not report anything: the runs that were
    # still going produced no result.
    terminal.show_interrupted()
    assert "interrupted" not in terminal.console.file.getvalue()


def test_rich_output_unordered_results():
    from rich.console import Console

    terminal = RichOutput(n_repetitions=1, show_progress=False, n_jobs=2)
    terminal.console = Console(file=io.StringIO(), width=120, highlight=False)

    runs = [
        ("data[n=1]", "obj", "fast"),
        ("data[n=2]", "obj", "fast"),
        # A slow run of the first dataset finishes after the second one.
        ("data[n=1]", "obj", "slow"),
    ]
    for data, obj, solver in runs:
        terminal.set(dataset=data, objective=obj, solver=solver)
        terminal.show_status(status='done')

    # The late result is grouped with the runs sharing its dataset, and no
    # dataset is displayed twice.
    assert list(terminal._lines()) == [
        "[bold]data\\[n=1][/]",
        "[dim]├── [/][bold]obj[/]",
        "[dim]│   [/][dim]├── [/][green]✓[/] fast [green]done[/]",
        "[dim]│   [/][dim]├── [/][green]✓[/] slow [green]done[/]",
        "[bold]data\\[n=2][/]",
        "[dim]├── [/][bold]obj[/]",
        "[dim]│   [/][dim]├── [/][green]✓[/] fast [green]done[/]",
    ]


def test_make_terminal_output(monkeypatch):
    # stdout is captured by pytest, hence not a terminal.
    assert type(make_terminal_output(1, True)) is TerminalOutput

    # The display can be turned off, from the config file or the environment.
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert type(make_terminal_output(1, True)) is RichOutput
    monkeypatch.setenv("BENCHOPT_NO_RICH", "true")
    assert type(make_terminal_output(1, True)) is TerminalOutput
    # Unlike a bare environment variable check, `0` does not disable it.
    monkeypatch.setenv("BENCHOPT_NO_RICH", "0")
    assert type(make_terminal_output(1, True)) is RichOutput


def test_rich_output_steps(tmp_path):
    log_file = tmp_path / "run.log"
    terminal = RichOutput(n_repetitions=1, show_progress=False)
    terminal.log_file = log_file
    log_file.write_text("run output\n")

    # The output of a step goes to the log, not on top of the spinner.
    with terminal.step("Saving results"):
        os.write(1, b"from the step\n")
    assert "from the step" in log_file.read_text()
    # The log is not overwritten by the step.
    assert "run output" in log_file.read_text()

    terminal.console = Console(file=io.StringIO(), width=120, highlight=False)
    terminal.show_outputs(results="res.parquet", report=None, log=log_file)
    display = terminal.console.file.getvalue()
    assert "res.parquet" in display and str(log_file) in display
    # Only the outputs that were produced are reported.
    assert "report" not in display


def test_rich_output_fits_the_screen():
    terminal = RichOutput(n_repetitions=1, show_progress=False, n_jobs=20)
    terminal.console = Console(file=io.StringIO(), width=80, height=20,
                               highlight=False)
    for i in range(20):
        terminal.start_run(dict(dataset_name=f"data{i}",
                                objective_name="obj", solver_name="s"))
    for i in range(30):
        terminal.set(dataset="data", objective="obj", solver=f"s{i}")
        terminal.show_status(status='done')

    display = _render_to_str(terminal).splitlines()
    # The display never overflows the screen, whatever the number of runs.
    assert len(display) <= 20
    # The counters are always visible, the sections are cropped instead.
    assert "done 30" in display[-1]
    assert any("more" in line for line in display)
    assert "Running" in "".join(display)


def test_rich_output_long_names_wrap_under_the_name():
    terminal = RichOutput(n_repetitions=1, show_progress=False)
    terminal.console = Console(file=io.StringIO(), width=80, highlight=False)
    terminal.set(dataset="data", objective="obj",
                 solver=f"gd[path={'x' * 200}]")
    terminal.show_status(status='done')

    terminal._print_results()
    lines = terminal.console.file.getvalue().splitlines()
    # The name is shown whole, wrapped past the guides instead of over them.
    assert all(len(line) <= 80 for line in lines)
    assert 'x' * 200 in "".join(line.strip("│├─ ") for line in lines)
    assert lines[-2].startswith("│   │     ")


def test_rich_output_running_probe():
    terminal = RichOutput(n_repetitions=1, show_progress=False, n_jobs=1)
    terminal.console = Console(file=io.StringIO(), width=120, height=20,
                               highlight=False)
    other = dict(META, solver_name="other[lr=1]")
    terminal.start_run(META)
    terminal.start_run(other)

    # A backend that knows which runs left the queue overrides the guess
    # based on the dispatch order.
    terminal.set_running_probe(lambda: [tuple(other.values())])
    display = _render_to_str(terminal)
    assert "other[lr=1]" in display
    assert "solver[lr=1e-3]" not in display

    # A probe that fails is dropped, rather than taking the run down.
    def _raise():
        raise RuntimeError("no scheduler here")

    terminal.set_running_probe(_raise)
    display = _render_to_str(terminal)
    assert "solver[lr=1e-3]" in display
    assert terminal._probe is None
