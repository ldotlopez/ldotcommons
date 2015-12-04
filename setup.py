# -*- encoding: utf-8 -*-

from distutils.core import setup

setup(
    name='ldotcommons',
    version='0.0.0.20141022.1',
    author='Luis López',
    author_email='ldotlopez@gmail.com',
    packages=['ldotcommons'],
    scripts=[],
    url='https://github.com/ldotlopez/ldotcommons',
    license='LICENSE.txt',
    description='Useful ldotlopez\'s stuff',
    long_description=open('README').read(),
    install_requires=[
        "aiohttp",
        "appdirs",
        "sqlalchemy",
    ],
)

