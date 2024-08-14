from benchopt.utils.safe_import import mock_all_import, mock_failed_import, _unmock_import, safe_import_context
from unittest.mock import Mock
import sys


def test_mock_all_import():
    mock_all_import()

    with safe_import_context() as import_ctx:
        import unknown_module
        import this

    assert isinstance(unknown_module, Mock)
    assert isinstance(this, Mock)

    sys.modules.pop('unknown_module')
    sys.modules.pop('this')

    _unmock_import()


def test_mock_failed_import():
    mock_failed_import()

    with safe_import_context() as import_ctx:
        import unknown_module
        import this

    assert isinstance(unknown_module, Mock)
    assert not isinstance(this, Mock)

    sys.modules.pop('unknown_module')
    sys.modules.pop('this')

    _unmock_import()

