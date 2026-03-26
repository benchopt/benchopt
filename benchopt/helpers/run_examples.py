import io
import re
import inspect
import weakref
from html import escape
from pathlib import Path
from uuid import uuid4

from benchopt.tests.utils import CaptureCmdOutput

# Shared state used by doc/conf.py to communicate sphinx-gallery context.
#
# Keys used in this module:
# - "paths": iterator of sphinx-gallery generated image paths used to derive
#   deterministic HTML output locations.
# - "build_dir": root output folder where generated HTML files are stored.
SPHINX_GALLERY_CTX = {
    'build_dir': Path() / "_build" / "html" / "auto_examples"
}

# Absolute path to the repository examples folder.
EXAMPLES_ROOT = Path(__file__).parents[2] / "examples"


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
        highlighted = f"<pre>{escape(code)}</pre>"
    else:
        highlighted = PygmentsBridge("html", "sphinx").highlight_block(
            code, language
        )
    return highlighted


def _html_to_replace_code_cell(html):
    "Replace the code block in sphinx-gallery examples with custom HTML"
    return f'<pre class="code-cell-equiv">{html}</pre>'


class HTMLCmdOutput:
    """Helper to display the output of a benchopt command in sphinx gallery.

    It replaces the cell calling the command with the actual command, display
    the console output, and embed the HTML result in the page.

    Parameters
    ----------
    cmd : str
        Command called in the CLI.
    output : str | None
        Standard output captured during the command call.
    result_html : str or None
        HTML content output by the command, or None when the command did
        not generate an HTML page.
    """
    def __init__(self, cmd, output, result_html):
        self.cmd = cmd
        self.cmd_html = _code_to_html(f"$ {cmd}", language="console")
        self.output_html = self.output_to_html(output)
        self.result_html = result_html

    def merge_lines(self, output):
        "Merge lines in the output that were overwritten using '\r'."
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
        "Process the output of the benchopt command to render in sphinx"
        if output is None:
            return ""
        output = self.merge_lines(output)
        # This allows to correctly display the progress in the example
        try:
            from rich.console import Console
            from rich.text import Text
        except ImportError:
            return f"<pre>{escape(output)}</pre>"
        console = Console(file=io.StringIO(), record=True, width=78)
        console.print(Text.from_ansi(output))
        output_html = console.export_html(
            inline_styles=True, code_format="<pre>{code}</pre>"
        )
        return f"""
            <div class="sphx-glr-script-out highlight-none notranslate">
                <div class="highlight">{output_html}</div>
            </div>
        """

    def embed_result_html(self):
        if self.result_html is None:
            return ""
        src_result_html = f"srcdoc='{escape(self.result_html)}'"
        if "paths" in SPHINX_GALLERY_CTX:
            # Save the result HTML to a file to be loaded in the iframe
            # for the doc
            html_path = next(SPHINX_GALLERY_CTX["paths"])
            html_path = Path(
                html_path.replace("images", "html_results")
            ).with_suffix('.html').resolve()
            html_path = html_path.relative_to(
                Path("auto_examples").resolve()
            )
            src_result_html = f"src='{html_path}'"

            html_path = SPHINX_GALLERY_CTX["build_dir"] / html_path
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(self.result_html, encoding='utf-8')

        return f"""
            <iframe class='benchmark_result' {src_result_html}
                    frameBorder='0' style='position: relative; width: 100%;'>
            </iframe>
        """

    def _repr_html_(self):
        """Generate the HTML representation for Sphinx-gallery.

        This is the part that is embedded in the generated documentation.
        Here we output the output of the command `output_html` as well as
        the resulting HTML page as an iframe.

        We also add a `pre` block with the command equivalent to the
        helper function called. This is used to replace the call in
        sphinx-gallery examples with the command line, to make it easier to
        reproduce outside of the documentation.
        """

        return inspect.cleandoc(f"""
            {_html_to_replace_code_cell(self.cmd_html)}
            {self.output_html}
            {self.embed_result_html()}
        """)


class HTMLBenchmarkDisplay:
    """Helper class to display a benchmark in Sphinx-gallery.

    This class is used to display a benchmark in an example in the doc from a
    given dictionary of filename and content. The display appears as multiple
    tabs in the doc.
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

        # create one tab per file in the `files` mapping.
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

        # Merge them and add the action if provided. The action is a text that
        # describes the change that was made to the benchmark files.
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
    - run the benchmark and display the results with :func:`benchopt_cli`.

    It has a ``name`` and ` ``benchmark_dir`` attribute. The benchmark_dir is
    a temporary folder ``temp_benchmark_XXXX/name`.

    ``base`` corresponds to an existing benchmark, from which all files which
    do not match ``ignore`` are copied. ``base`` can either be a direct path
    to a benchmark folder, or the name of a benchmark folder in
    the example folder.

    The extra args (``objective, datasets, solvers, plots, extra_files``)
    provide mapping between file name and content as string, which are added to
    the benchmark, overriding existing ones if necessary.

    The resulting benchmark can then be updated through the ``update`` method,
    which accepts component mappings for ``objective, datasets, solvers, plots,
     extra_files``.
    """

    def __init__(
        self,
        name=None,
        base=None,
        objective=None,
        datasets=None,
        solvers=None,
        plots=None,
        extra_files=None,
        ignore=(),
    ):
        self.name = name
        loaded = {}
        if base is not None:
            loaded = self._load_existing_benchmark(base)
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
            **self.files, no_default=True, name=self.name
        )
        self._bench = self._temp_benchmark_cm.__enter__()
        self._finalizer = weakref.finalize(
            self, self._temp_benchmark_cm.__exit__, None, None, None
        )
        self._bench.benchmark_dir = (
            self._bench.benchmark_dir.resolve().relative_to(Path.cwd())
        )

    @property
    def benchmark_dir(self):
        return self._bench.benchmark_dir

    def close(self):
        """Release the temporary benchmark directory."""
        if self._finalizer.alive:
            self._finalizer()

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

    def _repr_html_(self):
        return HTMLBenchmarkDisplay(self.files)._repr_html_()

    def _load_existing_benchmark(self, benchmark):
        benchmark_dir = Path(benchmark)
        if not benchmark_dir.exists():
            # If the path does not exist, try to find it in the examples folder
            benchmark_dir = EXAMPLES_ROOT / benchmark
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
                f"#loaded from {file_path}\n"
                + file_path.read_text(encoding="utf-8")
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
            value = {self._name_from_content(c): c for c in value}
        return {
            fname: inspect.cleandoc(content)
            for fname, content in value.items()
        }

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
        path.write_text(content, encoding="utf-8")


def get_example_file():
    """Get the name of the example file.

    This only works when called from ``benchopt_cli`` itself called by an
    example script.

    The target output folder is derived from example names ``run_*.py`` by
    replacing the prefix with ``output_``.
    """
    import sys
    file = sys._getframe(2).f_globals['__file__']
    if file is None or not file.endswith(".py") or "run_" not in file:
        return None
    file = Path(file)
    file = file.parent / file.name.replace("run_", "output_")
    return file.with_suffix("")


def benchopt_cli(cmd):
    """Run any benchopt CLI command and return output for sphinx-gallery.

    This is a general-purpose helper that invokes any ``benchopt`` command
    (``run``, ``plot``, ``install``, …), captures its console output, detects
    any HTML result file it produces, and returns an :class:`HTMLCmdOutput`
    that can be embedded in Sphinx-gallery examples.

    In the rendered documentation the helper call is replaced by the
    equivalent shell command, making examples easy to reproduce from the
    command line.

    Outside sphinx-gallery builds, this helper has side effects:

    - it may create an ``output_*.`` folder next to the ``run_*.py``
        example script when that caller can be detected;
    - it copies produced result files into that folder;
    - it prints the command and separators to stdout.

    Parameters
    ----------
    cmd : str
        Benchopt command arguments as a shell-like string (without the
        ``benchopt`` executable prefix). Examples::

            "run path/to/benchmark -n 5 -r 1"
            "install path/to/benchmark -s solver1"

        In sphinx-gallery builds, this helper automatically appends:

            - ``--no-display`` for ``run`` commands;
            - ``--yes`` for ``install`` commands.

    Returns
    -------
    HTMLCmdOutput
        An object whose ``_repr_html_`` renders the command, its console
        output, and any HTML result file produced — compatible with
        Sphinx-gallery.
    """
    import os
    import shlex
    from benchopt.cli import benchopt as benchopt_cli

    # Parse command arguments from a shell-like string.
    # On Windows, keep backslashes in paths (e.g. temp dirs) by using
    # non-posix parsing.
    cmd_parts = shlex.split(cmd.strip(), posix=(os.name != "nt"))
    cmd_str = f"benchopt {' '.join(cmd_parts)}"

    is_sphinx = "paths" in SPHINX_GALLERY_CTX

    extra_flags = {
        "install": ["--yes"] if is_sphinx else [],
        "run": ["--no-display"] if is_sphinx else [],
    }

    cli_cmd = cmd_parts[0]
    for flag in extra_flags.get(cli_cmd, []):
        if flag not in cmd_parts:
            cmd_parts.append(flag)

    output_dir = None
    if not is_sphinx:
        print(f"Running command:\n$ {cmd_str}")
        print("-" * 40)
        output_dir = get_example_file()
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)

    # Keep result files so we can read them before deciding to delete them.
    with CaptureCmdOutput(
        debug=not is_sphinx, delete_result_files=False
    ) as capture:
        benchopt_cli(cmd_parts, standalone_mode=False)

    # Find the first HTML file reported in the captured output and read it.
    result_html = None
    for f in capture.result_files:
        fpath = Path(f)
        # fetch the HTML result for display in the doc
        if fpath.suffix == '.html' and fpath.exists() and result_html is None:
            result_html = fpath.read_text(encoding='utf-8')
        # copy all files to the output dir if requested
        if output_dir is not None and not is_sphinx:
            (output_dir / fpath.name).write_bytes(fpath.read_bytes())

    if not is_sphinx:
        print("-" * 40)

    return HTMLCmdOutput(cmd_str, capture.output, result_html)
