from benchopt.base import BaseSolver


def assert_matlab_installed():
    import matlab


MATLAB_ENGINE = None # Global variable to store the matlab engine
def get_matlab_engine(paths, background=False):
    """
    Return a matlab engine. If it does not exist, start it.

    Parameters
    ----------
    paths : str or list of str
        Path to add to the matlab path.
    async : bool
        If True, start the engine in a separate process.

    Returns
    -------
    engine : matlab.engine
        The matlab engine.
    """
    import matlab.engine

    global MATLAB_ENGINE
    if MATLAB_ENGINE is None:
        MATLAB_ENGINE = matlab.engine.start_matlab(background=background)
    if isinstance(paths, str):
        paths = [paths]
    for path in paths:
        MATLAB_ENGINE.addpath(path)

    return MATLAB_ENGINE



class MatlabSolver(BaseSolver):

    requirements = ['pip:matlabengine', 'numpy']
