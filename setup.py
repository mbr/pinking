#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='pinking',
    version='0.1.dev1',
    description='A console-based GPIO GIU for Raspberry Pi. You don\'t need '
                'it, but you want it!',
    long_description=read('README.rst'),
    author='Marc Brinkmann',
    author_email='git@marcbrinkmann.de',
    url='http://github.com/mbr/pinking',
    license='MIT',
    install_requires=['click', 'logbook'],
    entry_points={
        'console_scripts': [
            'pinking = pinking.cli:main',
        ],
    }
)
