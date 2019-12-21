set DEFAULT_PYTEST_ARGS=-vlrx --timeout=60

call activate %VIRTUALENV%

pytest --junitxml=%JUNITXML% %DEFAULT_PYTEST_ARGS%
