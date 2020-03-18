#!/bin/bash

set -e

UNAMESTR=`uname`

if [[ "$UNAMESTR" == "Darwin" ]]; then
    # install OpenMP not present by default on osx
    HOMEBREW_NO_AUTO_UPDATE=1 brew install libomp

    # enable OpenMP support for Apple-clang
    export CC=/usr/bin/clang
    export CXX=/usr/bin/clang++
    export CPPFLAGS="$CPPFLAGS -Xpreprocessor -fopenmp"
    export CFLAGS="$CFLAGS -I/usr/local/opt/libomp/include"
    export CXXFLAGS="$CXXFLAGS -I/usr/local/opt/libomp/include"
    export LDFLAGS="$LDFLAGS -L/usr/local/opt/libomp/lib -lomp"
    export DYLD_LIBRARY_PATH=/usr/local/opt/libomp/lib
fi

make_conda() {
    TO_INSTALL="$@"
    conda create -n $VIRTUALENV --yes $TO_INSTALL
    source activate $VIRTUALENV
}

if [[ "$PACKAGER" == "conda" ]]; then
    TO_INSTALL=$(cat dev-requirements.txt)
    TO_INSTALL="python=$VERSION_PYTHON pip $TO_INSTALL"

	make_conda $TO_INSTALL

elif [[ "$PACKAGER" == "ubuntu" ]]; then
    sudo apt-get update
    sudo apt-get install python3-venv python3-virtualenv python3-numpy cython
    python3 -m virtualenv --system-site-packages --python=python3 $VIRTUALENV
    source $VIRTUALENV/bin/activate
    python -m pip install -r dev-requirements.txt
fi

python --version
python -c "import numpy; print('numpy %s' % numpy.__version__)"
python -c "from joblib import cpu_count; print('%d CPUs' % cpu_count())"
pip list
pip install -e .
