import io
import inspect
from html import escape
from pathlib import Path

from benchopt.tests.utils import CaptureCmdOutput
from benchopt.plotting.generate_html import get_results, render_all_results

# Used to monkey-patch sphinx-gallery behavior and retrieve a path iterator
SPHINX_GALLERY_CTX = {}

EXAMPLES_DIR = Path(__file__).parent.parent.parent / 'examples'
BUILD_DIR = Path() / "_build" / "html" / "auto_examples"


class HTMLResultPage:
    def __init__(self, result_html, output, cmd):
        self.max_height = 700

        self.cmd, self.cmd_html = cmd, self.cmd_to_html(cmd)
        self.output_html = self.output_to_html(output)
        self.result_html = result_html

    def merge_lines(self, output):
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

        from sphinx.highlighting import PygmentsBridge

        bridge = PygmentsBridge('html', 'sphinx')
        html = bridge.highlight_block(cmd, 'console')
        return html

    def _repr_html_(self):
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
    benchmark_name=None, benchmark_dir=None, n=5, r=1, config=None
):
    """Run a benchmark from benchopt.examples with benchopt.

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

    if benchmark_dir is None:
        benchmark_dir = EXAMPLES_DIR / benchmark_name

    benchmark = Benchmark(benchmark_dir)
    with CaptureCmdOutput() as out:
        save_file = run_benchmark(
            benchmark_dir, max_runs=n, n_repetitions=r,
            plot_result=False, no_cache=True
        )

        if config is None:
            config = benchmark.get_plot_config()
        html_root = Path('.')

        results = get_results(
            [save_file], html_root, benchmark, config=config
        )
        html = render_all_results(results, benchmark.name, home='#')[0]

    cmd = f"$ benchopt run {benchmark.name} -n {n} -r {r}"
    return HTMLResultPage(html, out.output, cmd)
