from setuptools import setup, find_packages

from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding= "utf-8") as f:
    long_description = f.read()

import sys
from setuptools.command.test import test as TestCommand

class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

version = "0.0.2"

setup(
    name= "iyore",
    version= version,
    description= "Ease the thistly problem of accessing data stored in arbitrary, consistent directory structures",
    long_description= long_description,
    url= "https://github.com/nationalparkservice/iyore",
    download_url= "https://github.com/nationalparkservice/iyore/tarball/{}".format(version),
    author= "Gabe Joseph",
    author_email= "gabriel_joseph@partner.nps.gov",

    keywords= "data filesystem science",
    classifiers = [],

    py_modules= ["iyore"],
    install_requires= ['future'],

    tests_require= ['pytest'],
    cmdclass= {'test': PyTest}

    )
