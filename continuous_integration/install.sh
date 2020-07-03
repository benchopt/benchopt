#!/bin/bash

set -e

UNAMESTR=`uname`

TO_INSTALL=$(cat dev-requirements.txt)
TO_INSTALL="python=$VERSION_PYTHON pip $TO_INSTALL"

conda create -n $CONDAENV --yes $TO_INSTALL
. activate $CONDAENV
echo $CONDA

python --version
python -c "import numpy; print('numpy %s' % numpy.__version__)"
python -c "from joblib import cpu_count; print('%d CPUs' % cpu_count())"
pip list
pip install -e .
