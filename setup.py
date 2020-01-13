#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from setuptools import setup, find_packages
import sys
import warnings

dynamic_requires = []

version = '0.2.1'

setup(
    name='Zemismart',
    version=version,
    url='https://github.com/GylleTanken/python-zemismart-roller-shade',
    packages=find_packages(),
    scripts=[],
    description='Python API for controlling Zemismart Roller Shade',
    classifiers=[
        'Development Status :: 1 - Beta',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    include_package_data=True,
    zip_safe=False,
)
