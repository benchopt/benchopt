#!/bin/bash

set -e

conda info
pip freeze

TEST_CMD="python -m pytest -vs --durations=20 --junitxml=$JUNIT_XML"
TEST_CMD="$TEST_CMD --test-env $CONDA_ENV"

# Un-comment when debugging the CI
# TEST_CMD="$TEST_CMD --skip-install"

if [[ "$COVERAGE" == "true" ]]; then
    export COVERAGE_PROCESS_START=".coveragerc"
    TEST_CMD="$TEST_CMD --cov=benchopt --cov-append"
    python continuous_integration/install_coverage_subprocess_pth.py
fi

set -x
$TEST_CMD
$TEST_CMD --skip-install --cov-append
set +x

if [[ "$COVERAGE" == "true" ]]; then
    coverage xml -i  # language agnostic report for the codecov upload script
fi
