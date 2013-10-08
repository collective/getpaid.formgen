from zope.interface import Interface


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

