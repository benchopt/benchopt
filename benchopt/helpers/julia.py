from contextlib import contextmanager

from benchopt.config import DEBUG
from benchopt.base import BaseSolver
from benchopt.utils.stream_redirection import SuppressStd
from benchopt.utils.shell_cmd import _run_shell_in_conda_env


# nullcontext is not available in python <=3.6 so we resort to this
# for backward compat.
@contextmanager
def nullcontext(enter_result=None):
    yield enter_result


def assert_julia_installed():
    import julia  # noqa: F401


# Singleton to get the julia interpreter only once
jl_interpreter = None


def get_jl_interpreter():
    global jl_interpreter
    if jl_interpreter is None:
        # Only suppress std if not in debug mode.
        out = nullcontext() if DEBUG else SuppressStd()
        try:
            with out:
                import julia
                # configure the julia runtime
                runtime_config = {
                    'compiled_modules': False,
                    'debug': bool(DEBUG)
                }
                julia.install()
                jl_interpreter = julia.Julia(**runtime_config)
        except BaseException:
            if hasattr(out, 'output'):
                print(out.output)
            raise

    return jl_interpreter


JULIA_PKG_INSTALL = """
using Pkg;
import Pkg.REPLMode: parse_package, QString

function parse_pkg(pkg::String)
    pkg = [QString(pkg, false)]
    return parse_package(pkg, []; add_or_dev=true)
end

for pkg in [{reqs}]
    Pkg.add(parse_pkg(pkg));
end
"""


class JuliaSolver(BaseSolver):

    # Requirements
    install_cmd = 'conda'
    requirements = ['julia', 'pip:julia']

    @classmethod
    def is_installed(cls, env_name=None, raise_on_not_installed=None):
        success = super().is_installed(
            env_name=env_name, raise_on_not_installed=raise_on_not_installed
        )

        # If julia is installed, check that the package dependencies are also
        # installed.
        if success and hasattr(cls, 'julia_requirements'):
            try:
                jl = get_jl_interpreter()
                for pkg in cls.julia_requirements:
                    jl.eval(f'using {pkg.split("::")[0]}')
            except Exception:
                return False
        return success

    @classmethod
    def _post_install_hook(cls, env_name=None):
        """Install dependencies on Julia packages"""

        if hasattr(cls, 'julia_requirements'):
            julia_pkg_install = JULIA_PKG_INSTALL.format(
                reqs=','.join([f'"{p.split("::")[-1]}"'
                               for p in cls.julia_requirements])
            )
            _run_shell_in_conda_env(
                f"julia -e '{julia_pkg_install}'", env_name=env_name,
                raise_on_error=True
            )
