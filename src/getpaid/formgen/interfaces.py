from zope import schema
from zope.interface import Interface

from zope.app.container.constraints import contains
from zope.app.container.constraints import containers

from getpaid.formgen import GPFGMessageFactory as _

class IMakePaymentProcess(Interface):
    """
    Fulfillment geric steps
    """
