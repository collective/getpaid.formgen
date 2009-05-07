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
    'GetPaidFormMailerAdapter' : 'PloneFormGen: Add GetPaid Mailer adapter',
}
setDefaultRoles(ADD_PERMISSIONS['GetpaidPFGAdapter'], ['Manager',])
setDefaultRoles(ADD_PERMISSIONS['GetPaidFormMailerAdapter'], ['Manager',])
