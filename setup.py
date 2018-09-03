# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from codecs import open
from os import path
import re

version = '0.0.1'

here = path.abspath(path.dirname(__file__))

readme_file = 'README.md'
try:
    from pypandoc import convert
    long_descr = convert(readme_file, 'rst', 'md')
    with open(path.join(here, 'README.rst'), 'w', encoding='utf-8') as f:
        f.write(long_descr)
except ImportError:
    print(
        "warning: pypandoc module not found, could not convert Markdown to RST")
    long_descr = open(readme_file).read()

# get the dependencies and installs
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    all_reqs = f.read().split('\n')

install_requires = [x.strip() for x in all_reqs if 'git+' not in x]
dependency_links = [x.strip().replace('git+', '') for x in all_reqs
                    if 'git+' not in x]



setup(name='ldndctools',
      version=version,
      description='This package contains preprocessing tools for LandscapeDNDC',
      long_description=long_descr,
      url='https://gitlab.com/cw_code/ldndc_raster_tools',
      author='Christian Werner',
      author_email='christian.werner@senckenberg.de',
      license='ND',
      download_url='https://gitlab.com/cw_code/ldndc_raster_tools/tarball/' + version,
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: LandscapeDNDC scientists',
          'Programming Language :: Python :: 3',
      ],
      keywords='LandscapeDNDC preprocessing input-generator',
      zip_safe= False,
      packages=find_packages(exclude=['docs', 'tests']),
      install_requires=install_requires,
      package_dir={'ldndctools': ['misc', 'soil', 'tmworld']},
      include_package_data=True,
      scripts=['NLCC', 'NLCC_split4db', 'DLSC'],
      dependency_links=dependency_links)

