import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


# Required dependencies
required = [
    'joblib',
    'numpy',
    'tqdm',
    'humanhash3',
    'python-dateutil'
]

setup(
    name="smallab",
    version="1.5.1",
    url='https://github.com/octopuscabbage/smallab',
    packages=find_packages(),
    install_requires=required,
    license="BSD 2-Clause License",
    description="smallab (Small Lab) is an experiment framework designed " + \
                "to be easy to use with your experiment",
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
)
