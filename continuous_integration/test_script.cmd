set DEFAULT_PYTEST_ARGS=-vlrx --timeout=60 --cov=benchopt

call activate %VIRTUALENV%

pytest --junitxml=%JUNITXML% %DEFAULT_PYTEST_ARGS%
