"""This is a a functional doctest test. It uses PloneTestCase and doctest
syntax. In the test itself, we use zope.testbrowser to test end-to-end
functionality, including the UI.

One important thing to note: zope.testbrowser is not JavaScript aware! For
that, you need a real browser. Look at zope.testbrowser.real and Selenium
if you require "real" browser testing.
"""

import os, sys

if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import unittest
import doctest
from Testing.ZopeTestCase import FunctionalDocFileSuite as Suite
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import _createObjectByType
from getpaid.formgen.tests import base_test_case
from getpaid.formgen.config import PROJECTNAME

from Products.PloneTestCase.PloneTestCase import PloneTestCase
from Products.PloneTestCase.PloneTestCase import setupPloneSite
from Products.PloneTestCase.PloneTestCase import FunctionalTestCase

setupPloneSite(products=base_test_case.PRODUCTS)

from getpaid.formgen.tests.util import list_acceptance_doctests

class AcceptanceFunctionalTest(FunctionalTestCase):
    def afterSetUp(self):
        pass

def test_suite():
    """This sets up a test suite that actually runs the tests in the class
    above
    """
    suite = unittest.TestSuite()
    filenames = list_acceptance_doctests()

    for docfile in filenames:     
        suite.addTest(Suite(docfile,
                            package='getpaid.formgen.tests',
                            test_class=AcceptanceFunctionalTest))

    return suite
