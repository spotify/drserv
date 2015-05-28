from setuptools import setup

install_requires = (
    'pyaml',
    'crtauth',
    'requests==2.6.0',
)

tests_require = (
    'nose'
)


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
    scripts=['bin/drserv-server', 'bin/drserv-client'],
    test_suite='nose.collector',
    install_requires=install_requires,
    tests_require=tests_require,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Build Tools',
    ],
)
