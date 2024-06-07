@echo off

setlocal enabledelayedexpansion

call conda info
if %errorlevel% neq 0 exit /b %errorlevel%

call conda install -y pytest
if %errorlevel% neq 0 exit /b %errorlevel%

pip freeze
if %errorlevel% neq 0 exit /b %errorlevel%

set TEST_CMD=python -m pytest -vs --durations=20 --junitxml=JUNIT_XML
set TEST_CMD=python -m pytest -vs --durations=20 --junitxml=JUNIT_XML --test-env CONDA_ENV

REM Un-comment when debugging the CI
REM set TEST_CMD=%TEST_CMD% --skip-install

if "%COVERAGE%"=="true" (
    set COVERAGE_PROCESS_START=.coveragerc
    set TEST_CMD=%TEST_CMD% --cov=benchopt --cov-append
    python continuous_integration\install_coverage_subprocess_pth.py
    if %errorlevel% neq 0 exit /b %errorlevel%
)

@echo on
%TEST_CMD%
if %errorlevel% neq 0 exit /b %errorlevel%
%TEST_CMD% --skip-install --cov-append
if %errorlevel% neq 0 exit /b %errorlevel%
@echo off

if "%COVERAGE%"=="true" (
    coverage xml -i
    if %errorlevel% neq 0 exit /b %errorlevel%
)

exit /b 0
