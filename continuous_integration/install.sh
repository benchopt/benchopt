#!/bin/bash

set -e

UNAMESTR=`uname`

TO_INSTALL=$(cat dev-requirements.txt)
TO_INSTALL="python=$VERSION_PYTHON pip $TO_INSTALL"

conda create -n $CONDAENV --yes $TO_INSTALL
. activate $CONDAENV
conda config --env --prepend channels conda-forge

echo $CONDA

python --version
python -c "import numpy; print('numpy %s' % numpy.__version__)"
python -c "from joblib import cpu_count; print('%d CPUs' % cpu_count())"
pip list
pip install -e .


# There is an ungoing issue with compat between libgit2 and julia which makes
# the auto install of julia solver fails when cloning the General repository
# from julia. To avoid this, we clone this on the system directly.
# See https://github.com/JuliaLang/julia/issues/33111
git clone https://github.com/JuliaRegistries/General.git \
        $HOME/.julia/registries/General
