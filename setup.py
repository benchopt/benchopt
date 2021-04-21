from setuptools import setup
import setuptools_scm  # noqa: F401
import toml  # noqa: F401


setup(
    entry_points={
        'console_scripts': ['benchopt = benchopt.cli:benchopt']
    }
)
