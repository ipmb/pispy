#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='pispy',
    version='0.0.0-dev',
    description="",
    #long_description=open('README.rst').read(),
    author="Peter Baumgarter",
    author_email='pete@lincolnloop.com',
    url='https://github.com/ipmb/pispy',
    license='BSD',
    install_requires=[
        'asyncio==0.2.1',
        'tornado==3.2',
        'sockjs-tornado==1.0',

    ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
