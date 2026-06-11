"""Backend-agnostic Python version helpers."""
import re

DEFAULT_PYTHON_VERSION = '3.12'


def _python_version_satisfies(env_version, required):
    """Check if `env_version` satisfies `required`.

    `required` may be an exact version string ('3.12') or
    a specifier ('>=3.12').
    """
    if re.match(r'^[><=!]', str(required)):
        from packaging.specifiers import SpecifierSet
        return env_version in SpecifierSet(required)
    return env_version.startswith(str(required))


def get_benchmark_python_version(benchmark):
    if benchmark is None:
        return DEFAULT_PYTHON_VERSION
    objective = benchmark.get_benchmark_objective()
    return getattr(objective, 'python_version', DEFAULT_PYTHON_VERSION)
