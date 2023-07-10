from contextlib import contextmanager

from benchopt.base import BaseSolver


def assert_julia_installed():
    import matlab

@contextmanager()
def matlab_engine(paths):
    """Context manager to start a matlab engine and close it properly.

    Parameters
    ----------
    paths : list of str or str
        List of paths to add to the matlab path.

    Yields
    ------
    eng : matlab.engine
        The matlab engine.
    """
    import matlab.engine
    eng = matlab.engine.start_matlab()
    if not isinstance(paths, list):
        paths = [paths]
    for path in paths:
        eng.addpath(path)
    yield eng
    eng.quit()



class MatlabSolver(BaseSolver):

    requirements = ['pip:matlabengine']
