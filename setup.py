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
    'python-dateutil',
    'dill',
    'scikit-learn'
]

setup(
    name="smallab",
    version="2.3.0",
    url='https://github.com/octopuscabbage/smallab',
    packages=find_packages(),
    install_requires=required,
    license="BSD 2-Clause License",
    description="smallab (Small Lab) is an experiment framework designed " + \
                "to be easy to use with your experiment",
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    entry_points={
        'console_scripts': [
            'smdash=smallab.dashboard.dashboard:run_dash_from_command_line',
    ],
    },
)

