def import_numba_warnings(name):
    """Import numba warning classes.

    Implemented:
    - "performance" : NumbaPerformanceWarning
    """
    if name == "performance":
        try:
            # numba 0.49
            from numba.core.errors import NumbaPerformanceWarning
        except ImportError:
            try:
                # numba 0.44
                from numba.errors import NumbaPerformanceWarning
            except ImportError:
                # numba 0.24
                from numba.errors import PerformanceWarning as \
                    NumbaPerformanceWarning
        return NumbaPerformanceWarning

    else:
        raise NotImplementedError()
