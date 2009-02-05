"""Common configuration constants
"""
GLOBALS = globals()

from Products.CMFCore.permissions import setDefaultRoles

PROJECTNAME = 'getpaid.formgen'

ADD_PERMISSIONS = {
    'GetpaidPFGAdapter' : 'PloneFormGen: Add GetPaid adapter',
}


