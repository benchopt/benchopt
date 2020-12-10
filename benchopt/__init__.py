from .runner import run_benchmark

# Base objects to construct a benchmark
from .base import BaseSolver
from .base import BaseDataset
from .base import BaseObjective

# Context to allow safe imports
from .utils.safe_import import safe_import_context

__version__ = '1.1.0.dev0'

__all__ = [
    'BaseSolver', 'BaseDataset', 'BaseObjective', 'safe_import_context',
    'run_benchmark', '__version__',
]
