# -*- encoding: utf-8 -*-

from setuptools import setup, find_packages
import os

version = '0.1'

setup(name='getpaid.formgen',
      version=version,
      description=u"PloneGetPaid♡PloneFormGen integration".encode('utf-8'),
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: GNU General Public License (GPL)"
        ],
      keywords='plone plonegetpaid ploneformgen',
      author='Daniel Holth',
      author_email='daniel.holth@exac.com',
      url='http://dingoskidneys.com/cgi-bin/hgwebdir.cgi/getpaid.formgen',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['getpaid'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'Products.DataGridField >= 1.6rc1',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
