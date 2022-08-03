#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('CHANGELOG.rst') as history_file:
    history = history_file.read()

requirements = [
                'sphinx',
                "sphinx-argparse",
                "sphinx_rtd_theme",
                'sphinx-jsonschema',
                'sphinxcontrib.blockdiag',
                ]

setup_requirements = ['pytest-runner', 'wheel', ]

test_requirements = ['pytest>=3',]

setup(
    author="Hrishikesh Ram",
    author_email='hrishikesh.ram@nist.gov',
    python_requires='>=3.5',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: NIST License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Python package to process electronic structure calculation data (e.g., continuum solvation free energy) and statistical mechanics data (e.g., NASA polynomials) from Gaussian16, Arkane and related software. ",
    install_requires=requirements,
    license="NIST license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='dft_toolbox',
    name='dft_toolbox',
    packages=find_packages(include=['dft_toolbox', 'dft_toolbox.*']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://git@gitlab.nist.gov/hnr2/dft-toolbox',
    version='0.0.0',
    zip_safe=False,
)
