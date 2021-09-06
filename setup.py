from setuptools import setup

setup(
    entry_points={
        'console_scripts': ['benchopt = benchopt.cli:benchopt']
    }
)
