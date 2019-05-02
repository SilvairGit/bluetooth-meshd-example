#!env python

from setuptools import setup, find_packages

with open("README.md", "r") as f:
    LONG_DESCRIPTION = f.read()

setup(
    name='bluetooth-meshd-example',
    version='0.0.1',
    author='Michał Lowas-Rzechonek',
    author_email='michal.lowas-rzechonek@silvair.com',
    description=(
        'Example of a Bluetooth Mesh application using bluetooh-meshd'
    ),
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=('test*', )),
    python_requires='>=3.6.0',
    install_requires=[
        'DBussy==1.1',
    ],
    entry_points=dict(
        console_scripts=[
            'meshd-client = meshd_example.client:main',
        ]
    ),
)
