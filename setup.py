#!/usr/bin/env python
# encoding: utf-8


from setuptools import setup


def readme():
    with open('README.rst') as f:
        return f.read()
    
setup(
    name="dvbboxes",
    version="0.1",
    py_modules=['dvbboxes'],
    author="Thomas Ayih-Akakpo",
    author_email="thomas.ayih-akakpo@gulfsat.mg",
    description="dvbbox cluster manager",
    long_description=readme(),
    license='Apache 2.0',
    include_package_data=True,
    entry_points={
        'console_scripts': ['dvbboxes=dvbboxes:cli'],
        },
)
