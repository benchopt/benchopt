import re
from setuptools import find_packages, setup

with open('benchopt/__init__.py') as f:
    infos = f.readlines()
for line in infos:
    if "__version__" in line:
        match = re.search(r"__version__ = '([^']*)'", line)
        __version__ = match.groups()[0]


DISTNAME = 'benchopt'
DESCRIPTION = "Benchmark toolkit for optimization"
MAINTAINER = 'T. Moreau'
MAINTAINER_EMAIL = 'thomas.moreau@inria.fr'
URL = 'https://github.com/benchopt/benchopt'
LICENSE = 'BSD (3-clause)'
VERSION = __version__

with open('README.rst', 'r') as fid:
    long_description = fid.read()

setup(
    name=DISTNAME,
    maintainer=MAINTAINER,
    maintainer_email=MAINTAINER_EMAIL,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/x-rst',
    license=LICENSE,
    version=VERSION,
    url=URL,
    packages=find_packages(),
    install_requires=['numpy', 'pandas', 'matplotlib',
                      'click', 'joblib'],
    entry_points={
        'console_scripts': ['benchopt = benchopt.cli:start']
    }
)
