#!/usr/bin/env python
from setuptools import setup
import stasher

repo = 'https://github.com/andreif/stasher'
version = stasher.__version__

setup(
    name='stasher',
    version=version,
    description=stasher.parser.description,
    keywords=['stash', 'travis', 'coverage'],
    url=repo,
    download_url='%s/tarball/%s' % (repo, version),
    author='Andrei Fokau',
    author_email='andrei@5monkeys.se',
    license='MIT',
    zip_safe=False,
    py_modules=['stasher'],
    install_requires=['requests==2.20.0'],
    entry_points={
        'console_scripts': [
            'stash = stasher:main',
        ],
    },
    classifiers=[
        'Environment :: Web Environment',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
