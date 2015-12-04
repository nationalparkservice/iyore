from setuptools import setup, find_packages

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

setup(
    name= "iyore",
    version= "0.0.1",
    description= "Ease the thistly problem of accessing data stored in arbitrary, consistent directory structures",
    url= "https://github.com/gjoseph92/iyore",
    author= "Gabe Joseph",
    author_email= "gjoseph92@gmail.com",

    py_modules= ["iyore"],
    install_requires= ['future'],

    tests_require= ['pytest'],
    cmdclass= {'test': PyTest}

    )
