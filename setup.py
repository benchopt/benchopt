
from setuptools import find_packages, setup

from benchopt import __version__

DISTNAME = 'benchopt'
DESCRIPTION = "Benchmark toolkit for optimization"
MAINTAINER = 'T. Moreau'
MAINTAINER_EMAIL = 'thomas.moreau@inria.fr'
URL = 'https://github.com/tommoral/benchopt'
LICENSE = 'BSD (3-clause)'
VERSION = __version__


setup(
    name=DISTNAME,
    maintainer=MAINTAINER,
    maintainer_email=MAINTAINER_EMAIL,
    description=DESCRIPTION,
    license=LICENSE,
    version=VERSION,
    url=URL,
    packages=find_packages(),
    install_requires=['numpy', 'pandas', 'matplotlib'],
    entry_points={
        'console_scripts': ['benchopt = benchopt.cli:start']
    }
)
