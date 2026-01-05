import io
import inspect
from html import escape
from pathlib import Path

from benchopt.tests.utils import CaptureCmdOutput
from benchopt.plotting.generate_html import get_results, render_all_results

# Used to monkey-patch sphinx-gallery behavior in doc/conf.py and
# retrieve a path iterator to store the HTML result files.
SPHINX_GALLERY_CTX = {}

# Output build dir for sphinx-gallery
BUILD_DIR = Path() / "_build" / "html" / "auto_examples"


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
        self.cmd, self.cmd_html = cmd, self.cmd_to_html(cmd)

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

    def cmd_to_html(self, cmd):
        """Convert the command to HTML with syntax highlighting."""
        try:
            from sphinx.highlighting import PygmentsBridge
        except ImportError:
            return f"$ {cmd}"

        bridge = PygmentsBridge('html', 'sphinx')
        html = bridge.highlight_block(f"$ {cmd}", 'console')
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
            <pre class="cmd-equiv"> {self.cmd_html}</pre>
            <div class="sphx-glr-script-out highlight-none notranslate">
                <div class="highlight">{self.output_html}</div>
            </div>
            <iframe class="benchmark_result" {src_result_html} frameBorder='0'
                    style="position: relative; width: 100%;"></iframe>
        """)


def benchopt_run(
    benchmark_name=None, benchmark_dir=None, n=5, r=1, plot_config=None
):
    """Run a benchmark and return output compatible with sphinx-gallery.

    Parameters
    ----------
    benchmark_name : str
        Name of the benchmark to run. Must be one of the benchmarks in
        `examples`.
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
    if benchmark_dir is None:
        import inspect
        example_dir = Path(inspect.stack()[1].filename).parent
        benchmark_dir = (example_dir / benchmark_name).resolve()

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
