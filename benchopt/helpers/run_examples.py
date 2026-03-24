import io
import re
import inspect
import weakref
from html import escape
from pathlib import Path
from uuid import uuid4

from benchopt.tests.utils import CaptureCmdOutput
from benchopt.plotting.generate_html import get_results, render_all_results

# Used to monkey-patch sphinx-gallery behavior in doc/conf.py and
# retrieve a path iterator to store the HTML result files.
SPHINX_GALLERY_CTX = {}

# Output build dir for sphinx-gallery
BUILD_DIR = Path() / "_build" / "html" / "auto_examples"

EXT_TO_LANGUAGE = {
    ".py": "python",
    ".jl": "julia",
    ".r": "r",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".rst": "rst",
}


def _code_to_html(code, language=None, filename=None):
    if language is None and filename is not None:
        language = EXT_TO_LANGUAGE.get(
            Path(filename).suffix, "text"
        )
    try:
        from sphinx.highlighting import PygmentsBridge
    except ImportError:
        highlighted = f"<pre>{escape(inspect.cleandoc(code))}</pre>"
    else:
        highlighted = PygmentsBridge("html", "sphinx").highlight_block(
            inspect.cleandoc(code), language
        )
    return highlighted


def _html_to_replace_code_cell(html):
    "Replace the code block in sphinx-gallery examples with custom HTML"
    return f'<pre class="code-cell-equiv">{html}</pre>'


class HTMLResultPage:
    """Class to capture a benchmark output in HTML format for Sphinx-gallery.

    Parameters
    ----------
    result_html : str
        HTML content of the benchmark result.
    output : str
        Standard output captured during the benchmark run.
    cmd : str
        Command used to run the benchmark.
    """
    def __init__(self, result_html, output, cmd):
        self.result_html = result_html
        self.output_html = self.output_to_html(output)
        self.cmd = cmd
        self.cmd_html = _code_to_html(f"$ {cmd}", language="console")

    def merge_lines(self, output):
        """Merge lines in the output that were overwritten using '\r'."""
        out = []
        cursor = start_line = 0
        for c in output:
            if c == '\r':
                cursor = start_line
            elif c == '\n':
                out.append(c)
                cursor = start_line = len(out)
            else:
                if cursor == len(out):
                    out.append(c)
                else:
                    out[cursor] = c
                cursor += 1
        return ''.join(out)

    def output_to_html(self, output):
        """Process the output of the benchopt command to render in sphinx"""
        output = self.merge_lines(output)
        # This allows to correctly display the progress in the example
        from rich.console import Console
        from rich.text import Text
        console = Console(file=io.StringIO(), record=True, width=78)
        console.print(Text.from_ansi(output))
        html = console.export_html(
            inline_styles=True, code_format="<pre>{code}</pre>"
        )
        return html

    def _repr_html_(self):
        """Generate the HTML representation for Sphinx-gallery.

        This is the part that is embedded in the generated documentation.
        Here we output the output of the command `output_html` as well as
        the resulting HTML page as an iframe.

        We also add a `pre` block with the command equivalent to the
        `benchopt_run` function called. This is used to replace the call in
        sphinx-gallery examples with the command line, to make it easier to
        reproduce outside of the documentation.
        """
        src_result_html = f"srcdoc='{escape(self.result_html)}'"
        if "paths" in SPHINX_GALLERY_CTX:
            # Save the result HTML to a file to be loaded in the iframe
            # for the doc
            html_path = next(SPHINX_GALLERY_CTX["paths"])
            html_path = Path(
                html_path.replace("images", "html_results")
            ).with_suffix('.html')
            html_path = html_path.relative_to(Path("auto_examples").resolve())
            src_result_html = f"src='{html_path}'"

            html_path = BUILD_DIR / html_path
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(self.result_html, encoding='utf-8')

        return inspect.cleandoc(f"""
            {_html_to_replace_code_cell(self.cmd_html)}
            <div class="sphx-glr-script-out highlight-none notranslate">
                <div class="highlight">{self.output_html}</div>
            </div>
            <iframe class="benchmark_result" {src_result_html} frameBorder='0'
                    style="position: relative; width: 100%;"></iframe>
        """)


class HTMLBenchmarkDisplay:
    """Helper class to display a benchmark in Sphinx-gallery.

    This class is used to create a temporary benchmark from given component
    strings, and display it as HTML tabs in the documentation. It also allows
    to run the benchmark and capture the output in a format compatible with
    Sphinx-gallery.
    """

    def __init__(self, files, action=None):
        self.action = action
        self.files = []
        for key in files:
            if key != "objective" and len(files[key]) > 0:
                self.files.extend(
                    (f"{key}/{fn}" if key != "extra_files" else fn, content)
                    for fn, content in files[key].items()
                )
            elif key == "objective":
                self.files.append((f"{key}.py", files[key]))
        # files.extend(sorted(self.extra_files.items()))

    def _repr_html_(self):
        tabs_id = f"example-benchmark-{uuid4().hex}"
        if len(self.files) == 0:
            return "<pre>No benchmark files.</pre>"

        items = []
        for idx, (label, content) in enumerate(self.files):
            input_id = f"{tabs_id}-{idx}"
            checked = 'checked="checked"' if idx == 0 else ""
            items.append(
                f"<input {checked} id='{input_id}' "
                f"name='{tabs_id}' type='radio'>"
                f"<label for='{input_id}'>{escape(label)}</label>"
                "<div class='sd-tab-content'>"
                f"{_code_to_html(content, filename=label)}</div>"
            )

        action = "" if self.action is None else f"<p>{self.action}</p><br/>"
        tabs = "\n".join(items)
        return _html_to_replace_code_cell(inspect.cleandoc(f"""
            <div class='display_example_benchmark'>
                {action}
                <div class='sd-tab-set'>
                    {tabs}
                </div>
            </div>"
        """))


class ExampleBenchmark:
    """Temporary benchmark helper tailored for documentation examples.

    This helper relies on :func:`benchopt.utils.temp_benchmark.temp_benchmark`
    underneath, but exposes a higher-level API suited for tutorial examples:

    - render benchmark files as compact HTML tabs;
    - create a benchmark either from explicit component strings or from an
      existing benchmark directory;
    - update the objective or add datasets/solvers incrementally;
    - run the benchmark and display the results with :func:`benchopt_run`.
    """

    def __init__(
        self,
        benchmark=None,
        objective=None,
        datasets=None,
        solvers=None,
        plots=None,
        extra_files=None,
        ignore=(),
    ):
        loaded = {}
        if benchmark is not None:
            loaded = self._load_existing_benchmark(benchmark)
            for key in loaded:
                loaded[key] = {
                    fname: content for fname, content in loaded[key].items()
                    if fname not in ignore
                } if key != "objective" else loaded[key]

        self.files = {}
        if objective is not None:
            self.files["objective"] = objective
        elif "objective" in loaded:
            self.files["objective"] = loaded["objective"]
        self.files.update({
            "datasets": {
                **loaded.get("datasets", {}),
                **self._to_component_dict(datasets),
            },
            "solvers": {
                **loaded.get("solvers", {}),
                **self._to_component_dict(solvers),
            },
            "plots": {
                **loaded.get("plots", {}),
                **self._to_component_dict(plots),
            },
            "extra_files": {
                **loaded.get("extra_files", {}),
                **self._to_component_dict(extra_files),
            },
        })

        from benchopt.utils.temp_benchmark import temp_benchmark

        self._temp_benchmark_cm = temp_benchmark(
            **self.files, no_default=True,
        )
        self._bench = self._temp_benchmark_cm.__enter__()
        self._finalizer = weakref.finalize(
            self, self._temp_benchmark_cm.__exit__, None, None, None
        )

    @property
    def benchmark_dir(self):
        return self._bench.benchmark_dir

    def close(self):
        """Release the temporary benchmark directory."""
        if self._finalizer.alive:
            self._finalizer()

    def _repr_html_(self):
        return HTMLBenchmarkDisplay(self.files)._repr_html_()

    def update(self, objective=None, datasets=None, solvers=None,
               plots=None, extra_files=None):
        """Update the benchmark files and return a display object."""
        files = {
            "datasets": self._to_component_dict(datasets),
            "solvers": self._to_component_dict(solvers),
            "plots": self._to_component_dict(plots),
            "extra_files": self._to_component_dict(extra_files),
        }
        if objective is not None:
            files["objective"] = objective
            self.files["objective"] = objective
            self._write_file(self.benchmark_dir / "objective.py", objective)

        for key in ["datasets", "solvers", "plots"]:
            self.files[key].update(files[key])
            for fname, content in files[key].items():
                self._write_file(self.benchmark_dir / key / fname, content)

        self.files["extra_files"].update(files["extra_files"])
        for fname, content in files["extra_files"].items():
            self._write_file(self.benchmark_dir / fname, content)

        return HTMLBenchmarkDisplay(
            files, action="We now update the following files:"
        )

    def _load_existing_benchmark(self, benchmark):
        benchmark_dir = Path(benchmark)
        if not benchmark_dir.exists():
            # If the path does not exist, try to find it in the examples folder
            benchmark_dir = (
                Path(__file__).parents[2] / "examples" / benchmark
            )
        if not benchmark_dir.exists():
            raise ValueError(
                f"Could not find benchmark at {benchmark} or "
                f"{benchmark_dir}"
            )

        objective = (benchmark_dir / "objective.py").read_text(
            encoding="utf-8"
        )
        datasets = self._read_component_dir(benchmark_dir / "datasets")
        solvers = self._read_component_dir(benchmark_dir / "solvers")
        plots = self._read_component_dir(benchmark_dir / "plots")
        extra_files = {
            file_path.relative_to(benchmark_dir).as_posix():
                file_path.read_text(encoding="utf-8")
            for file_path in benchmark_dir.rglob("*.yml")
        }

        return dict(
            objective=objective,
            datasets=datasets,
            solvers=solvers,
            plots=plots,
            extra_files=extra_files,
        )

    def _read_component_dir(self, directory):
        return {
            file_path.name: file_path.read_text(encoding="utf-8")
            for file_path in sorted(directory.glob("*.py"))
            if file_path.name != "__init__.py"
        }

    def _to_component_dict(self, value):
        if value is None:
            return {}
        if isinstance(value, str):
            value = [value]
        if isinstance(value, list):
            return {self._name_from_content(c): c for c in value}
        return dict(value)

    @staticmethod
    def _name_from_content(content):
        match = re.search(
            r'^\s*name\s*=\s*["\'](\w[^"\']*)["\']', content, re.MULTILINE
        )
        if match:
            name = re.sub(r'[^a-z0-9]+', '_', match.group(1).lower())
            name = name.strip('_')
            return f"{name}.py"
        raise ValueError(
            f"Could not extract name from content:\n{content[:200]}"
        )

    def _write_file(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(inspect.cleandoc(content), encoding="utf-8")


def benchopt_run(benchmark_dir=None, n=5, r=1, plot_config=None):
    """Run a benchmark and return output compatible with sphinx-gallery.

    Parameters
    ----------
    benchmark_dir : str or Path, optional
        Path to the benchmark to run. This is used instead of `benchmark_name`
        if provided.
    n : int, default=5
        Maximal number of iterations used for iterative solvers.
    r : int, default=1
        Number of times to repeat each experiment.
    """

    from benchopt.runner import run_benchmark
    from benchopt.benchmark import Benchmark

    is_sphinx = "paths" in SPHINX_GALLERY_CTX

    benchmark = Benchmark(benchmark_dir)
    cmd = f"benchopt run {benchmark.name} -n {n} -r {r}"

    if not is_sphinx:
        print(f"Running command:\n{cmd}")
        print("-" * 40)

    # Don't capture output when running the example outside of sphinx build
    with CaptureCmdOutput(debug=not is_sphinx) as out:
        save_file = run_benchmark(
            benchmark_dir, max_runs=n, n_repetitions=r,
            plot_result=False, no_cache=True
        )

        # plot the results to generate the HTML
        html_root = Path('.')
        if plot_config is None:
            plot_config = benchmark.get_plot_config()
        if "plots" not in plot_config or plot_config["plots"] is None:
            plot_config["plots"] = benchmark.get_plot_names()

        results = get_results(
            [save_file], html_root, benchmark, config=plot_config
        )
        html = render_all_results(results, benchmark, home='#')[0]
    if not is_sphinx:
        print("-" * 40)

    return HTMLResultPage(html, out.output, cmd)
