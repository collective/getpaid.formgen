"""Common configuration constants
"""
GLOBALS = globals()
product_globals = GLOBALS

from Products.CMFCore.permissions import setDefaultRoles

PROJECTNAME = 'getpaid.formgen'

DEPENDENCIES = []
PRODUCT_DEPENDENCIES = []
ADD_PERMISSIONS = {
    'GetpaidPFGAdapter' : 'PloneFormGen: Add GetPaid adapter',
}


