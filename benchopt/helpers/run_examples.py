import io
from html import escape
from uuid import uuid4
from pathlib import Path

from benchopt.tests.utils import CaptureCmdOutput
from benchopt.plotting.generate_html import get_results, render_all_results

EXAMPLES_DIR = Path(__file__).parent.parent.parent / 'examples'


class HTMLResultPage:
    def __init__(self, html, output, cmd):
        self.uid = uuid4().hex
        self.max_height = 700
        self.html = escape(html)
        self.cmd_html = self.cmd_to_html(cmd)
        self.output_html = self.output_to_html(output)

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
        # Another option is to use ansi2html
        # from ansi2html import Ansi2HTMLConverter
        # conv = Ansi2HTMLConverter()
        # html = conv.convert(output, full=False)
        # print(conv.produce_headers())
        return html

    def cmd_to_html(self, cmd):

        from sphinx.highlighting import PygmentsBridge

        bridge = PygmentsBridge('html', 'sphinx')
        html = bridge.highlight_block(cmd, 'console')
        return html

    def _repr_html_(self):
        return f"""
<pre id="cmd-{self.uid}">
    {self.cmd_html}
</pre>
<script>
function setup_{self.uid}(){{
    setTimeout(() => {{
        var iframe = document.getElementById("result-{self.uid}");
        iframe.height = iframe.contentWindow.document.body.scrollHeight;
        console.log(iframe.height)
    }}, "100");

    // Replace the command by the equivalent CLI call
    var cmd = document.getElementById("cmd-{self.uid}");
    var code_elem = cmd.parentElement.previousElementSibling;
    code_elem.firstChild.firstChild.innerHTML = cmd.children[0].children[0].innerHTML;
    cmd.setAttribute("style", "display: none;");

}}
</script>
<div class="sphx-glr-script-out highlight-none notranslate">
    <div class="highlight">
        {self.output_html}
    </div>
</div>
<iframe id="result-{self.uid}" class="benchmark_result" srcdoc='{self.html}'
        frameBorder='0' style="position: relative; width: 100%;"
        onload='setup_{self.uid}()'>
</iframe>
"""


def benchopt_run(benchmark_name, n=5, r=1, config=None):
    """Run a benchmark from benchopt.examples with benchopt.

    Parameters
    ----------
    benchmark_name : str
        Name of the benchmark to run. Must be one of the benchmarks in
        `benchopt.helpers.examples`.
    n : int, default=5
        Maximal number of iterations used for iterative solvers.
    r : int, default=1
        Number of times to repeat each experiment.
    """
    from benchopt.runner import run_benchmark

    benchmark_dir = EXAMPLES_DIR / benchmark_name
    from benchopt.benchmark import Benchmark

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

    cmd = f"$ benchopt run {benchmark_name} -n {n} -r {r}"
    return HTMLResultPage(html, out.output, cmd)
