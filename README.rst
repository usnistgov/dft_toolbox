===========
DFT Toolbox
===========


.. image:: https://git@gitlab.nist.gov/jac16/dft-toolbox/badges/master/pipeline.svg
    :target: https://git@gitlab.nist.gov/jac16/dft-toolbox/pipelines/
    :alt: Build Status

.. image:: https://git@gitlab.nist.gov/jac16/dft-toolbox/badges/master/coverage.svg
    :target: https://git@gitlab.nist.gov/jac16/dft-toolbox/pipelines/
    :alt: Coverage

.. image:: https://img.shields.io/badge/License-NIST license-blue.svg
    :target: https://git@gitlab.nist.gov/jac16/dft-toolbox/-/blob/master/LICENSE


Python package to process electronic structure calculation data (e.g., continuum solvation free energy) and statistical mechanics data (e.g., NASA polynomials) from Gaussian16, Arkane and related software. 


* Free software: NIST license

* Documentation: `python -m dft_toolbox -d`

Installation
------------

1. Download the master branch from our github page as a zip file, or clone it with git via ``https://git@gitlab.nist.gov/jac16/dft-toolbox`` to your working directory.
2. After changing directories, install with ``python setup.py install --user`` .

Contents and Features
----------------------

* *List features here*

Examples
---------

We have provided a notebook of examples that calculate the free energy of solvation, in ``dft_toolbox/notebooks/DFT_Toolbox_Code_Snippets.ipynb``.

Credits
-------

Development Lead(s): Hrishikesh Ram ( hrishikesh.ram@nist.gov ), Jennifer A. Clark ( jennifer.clark@nist.gov )

Principle Investigator: Jack F. Douglas ( jack.douglas@nist.gov )

This package was created with Cookiecutter_ and the `cookiecutter-nist-python`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-nist-python`: https://gitlab.nist.gov/gitlab/jac16/cookiecutter-nist-python
