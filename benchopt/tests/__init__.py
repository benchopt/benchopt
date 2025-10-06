from joblib.externals.cloudpickle import register_pickle_by_value

# Make sure the test cases in test_runner are pickleable as dynamic classes
from benchopt.tests import test_runner  # noqa: E402
register_pickle_by_value(test_runner)
