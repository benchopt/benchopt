#!/bin/bash

set -e

UNAMESTR=`uname`

TO_INSTALL="python=$VERSION_PYTHON pip"

conda create -n $CONDAENV --yes $TO_INSTALL
. activate $CONDAENV
conda config --env --prepend channels conda-forge

echo $CONDA

python --version
pip install -e .[test]


python -c "import numpy; print('numpy %s' % numpy.__version__)"
python -c "from joblib import cpu_count; print('%d CPUs' % cpu_count())"
pip list
