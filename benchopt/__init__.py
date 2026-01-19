from .runner import run_benchmark

# Base objects to construct a benchmark
from .base import BaseSolver
from .base import BaseDataset
from .base import BaseObjective
from .plotting.base import BasePlot

# Context to allow safe imports
from .utils.safe_import import safe_import_context

__version__ = "1.8.0"

__all__ = [
    'BaseSolver', 'BaseDataset', 'BaseObjective', 'BasePlot',
    'safe_import_context', 'run_benchmark', '__version__',
]
