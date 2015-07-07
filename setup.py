import sys
from setuptools import setup
from setuptools.command.test import test as TestCommand


install_requires = (
    'pyaml',
    'crtauth',
    'six',
    'requests==2.6.0',
)

tests_require = (
    'pytest-cov',
    'pytest-cache',
    'pytest-quickcheck',
    'tox',
)

setup_requires = (
    'flake8',
)


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = [
            'test',
            '-v',
            '--cov=drserv',
            '--cov-report=xml',
            '--cov-report=term-missing',
            '--result-log=pytest-results.log'
        ]
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(
    name='drserv',
    version='0.1.0',
    url='https://github.com/spotify/drserv',
    author='Client Build Squad @ Spotify',
    author_email='client-build@spotify.com',
    description=('RESTful service for publishing packages to debian '
                 'repositories'),
    license='Apache 2.0',
    packages=['drserv'],
    install_requires=install_requires,
    tests_require=tests_require,
    setup_requires=setup_requires,
    cmdclass={
        'test': PyTest,
    },
    entry_points={
        'console_scripts': [
            'drserv-server = drserv.server:main',
            'drserv-client = drserv.client:main'
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Build Tools',
    ],
)
