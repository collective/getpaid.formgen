import unittest
from Testing import ZopeTestCase as ztc
from Products.Five import zcml
from Products.PloneTestCase.PloneTestCase import setupPloneSite
from Products.PloneTestCase.layer import onsetup
from Products.PloneGetPaid.tests.base import PloneGetPaidFunctionalTestCase

ztc.installProduct('DataGridField')
ztc.installProduct('PloneGetPaid')
ztc.installProduct('PloneFormGen')

@onsetup
def load_zcml():
    import getpaid.formgen
    zcml.load_config('configure.zcml', getpaid.formgen)
    
    ztc.installPackage('getpaid.formgen')

load_zcml()
setupPloneSite(products=['getpaid.formgen'])

def test_suite():
    """This sets up a test suite that actually runs the tests in the class
    above
    """
    suite = unittest.TestSuite()
    suite.addTest(ztc.FunctionalDocFileSuite('test_functional_oneshot_success.txt',
                        package='getpaid.formgen.tests',
                        test_class=PloneGetPaidFunctionalTestCase))
    return suite
