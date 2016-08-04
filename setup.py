# -*- encoding: utf-8 -*-

from distutils.core import setup

fh = open("requirements.txt")
pkgs = filter(lambda line: line and line[0] >= 'a' and line[0] <= 'z',
              fh.readlines())
pkgs = list(pkgs)

setup(
    name='appkit',
    version='0.0.0.20160804.1',
    author='Luis López',
    author_email='ldotlopez@gmail.com',
    packages=['appkit'],
    scripts=[],
    url='https://github.com/ldotlopez/appkit',
    license='LICENSE.txt',
    description='Application toolkit',
    long_description=open('README').read(),
    install_requires=pkgs,
)
