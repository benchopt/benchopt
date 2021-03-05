import re
from setuptools import find_packages, setup

with open('benchopt/__init__.py') as f:
    infos = f.readlines()
for line in infos:
    if "__version__ =" in line:
        match = re.search(r"__version__ = '([^']*)'", line)
        __version__ = match.groups()[0]
        break


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
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: R',
        'Topic :: Scientific/Engineering',
        'Topic :: Utilities',
        'Topic :: Software Development :: Libraries',
    ],
    project_urls={
        'Documentation': 'https://benchopt.github.io/',
        'Source': 'https://github.com/benchopt/benchOpt',
        'Tracker': 'https://github.com/benchopt/benchOpt/issues/',
    },
    packages=find_packages(),
    install_requires=['numpy', 'scipy', 'pandas', 'matplotlib',
                      'click', 'joblib', 'pygithub', 'psutil'],
    entry_points={
        'console_scripts': ['benchopt = benchopt.cli:benchopt']
    }
)
