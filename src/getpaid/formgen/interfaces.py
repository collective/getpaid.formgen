from zope import schema
from zope.interface import Interface

from zope.app.container.constraints import contains
from zope.app.container.constraints import containers

from getpaid.formgen import GPFGMessageFactory as _

class IMakePaymentProcess(Interface):
    """
    Fulfillment geric steps
    """
try:
    from Products.PloneGetPaid.interfaces import ICreateTransientOrder
except:
    #This is only to make it work with current version of getpaid (0.6.1)
    class ICreateTransientOrder(Interface):
        """
        A transient order used by checkout forms and finally persisted
        """

