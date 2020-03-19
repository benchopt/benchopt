#!/bin/bash

set -e

if [[ "$PACKAGER" == "conda" ]]; then
    source activate $VIRTUALENV
elif [[ "$PACKAGER" == "ubuntu" ]]; then
    source $VIRTUALENV/bin/activate
fi

TEST_CMD="python -m pytest -v --showlocals --durations=20 --junitxml=$JUNITXML --pyargs"

# Un-comment when debugging the CI
# TEST_CMD="$TEST_CMD --skip-install"

if [[ "$COVERAGE" == "true" ]]; then
    TEST_CMD="$TEST_CMD --cov=benchopt --cov-append"
fi

set -x
$TEST_CMD
set +x

if [[ "$COVERAGE" == "true" ]]; then
    # coverage combine --append
    coverage xml -i  # language agnostic report for the codecov upload script
fi
