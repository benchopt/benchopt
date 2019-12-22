#!/bin/bash

set -e

if [[ "$PACKAGER" == "conda" ]]; then
    source activate $VIRTUALENV
elif [[ "$PACKAGER" == "ubuntu" ]]; then
    source $VIRTUALENV/bin/activate
fi

TEST_CMD="python -m pytest --showlocals --durations=20 --junitxml=$JUNITXML --pyargs"

# if [[ "$COVERAGE" == "true" ]]; then
#     TEST_CMD="$TEST_CMD --cov benchopt"
# fi

set -x
$TEST_CMD
set +x
