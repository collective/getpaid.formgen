#GetPaid imports
from Products.PloneGetPaid.interfaces import IGetPaidManagementOptions
from getpaid.core import interfaces, options
from getpaid.core.order import Order
from getpaid.formgen.interfaces import ICreateTransientOrder #It is a getpaid import, with a tweak

#Local imports
from getpaid.formgen.interfaces import IMakePaymentProcess

#Zope imports
from zope import interface, component
from zope.app import zapi
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent

#Plone imports
from Products.CMFCore.utils import getToolByName

#Other imports
from cPickle import loads, dumps
from AccessControl import getSecurityManager

class CreateTransientOrder( object ):
    """
    A really transient order
    """
    interface.implements(ICreateTransientOrder)

    def __call__( self, adapters, shopping_cart=None ):
        order = Order()

        portal = zapi.getSiteManager()
        portal = getToolByName(portal,'portal_url').getPortalObject()
        if shopping_cart is None:
            """
            This deservers a bit of explanation, when using the formgen adapter
            for 'disposable' carts (this means that we don't use the site's
            cart but a transient one just for the ocasion) we want this cart
            to be different from the user's one and to cease to exist after
            the transaction (means no persistence) .
            """
            shopping_cart =  component.getUtility( interfaces.IShoppingCartUtility ).get( portal )
        formSchemas = component.getUtility( interfaces.IFormSchemas )

        order.shopping_cart = shopping_cart

        for section in ('contact_information','billing_address','shipping_address'):
            interface = formSchemas.getInterface(section)
            bag = formSchemas.getBagClass(section).frominstance(adapters[interface])
            setattr(order,section,bag)

        order_manager = component.getUtility( interfaces.IOrderManager )        
        order.order_id = order_manager.newOrderId()
        
        order.user_id = getSecurityManager().getUser().getId()

        return order

class MakePaymentProcess( object ):
    """
    The generic steps included in the make payment steps
    """
    interface.implements(IMakePaymentProcess)
        
    def __init__( self, context, adapters ):
        manage_options = IGetPaidManagementOptions( context )
        processor_name = manage_options.payment_processor
        if not processor_name:
            raise RuntimeError( "No Payment Processor Specified" )
        self.processor_name = processor_name
        self.processor = component.getAdapter( context,
                                               interfaces.IPaymentProcessor,
                                               processor_name )
        self.adapters = adapters
        #self.order = CreateTransientOrder()
        self.order = None
        self.context = context
        
    def __call__( self, oneshot=None ):
        """
        If called as oneshot it will not use the site's cart, instead oneshot
        should be the cart to use
        """

        shopping_cart = oneshot
        if oneshot is None:
            #If this is not to be a disposable cart transaction we get the cart as we should.
            #NOTICE: This has not been tested since there is no process currently that uses it
            shopping_cart = component.getUtility( interfaces.IShoppingCartUtility ).get( self.context )
            shopping_cart = loads( dumps( shopping_cart ) )

        order_factory = CreateTransientOrder()
        self.order = order_factory( self.adapters, shopping_cart )
        notify( ObjectCreatedEvent( self.order ) )
        self.order.processor_id = self.processor_name
        self.order.finance_workflow.fireTransition( "create" )
        
        # extract data to our adapters
        formSchemas = component.getUtility(interfaces.IFormSchemas)
        result = self.processor.authorize( self.order, self.adapters[formSchemas.getInterface('payment')] )
        if result is interfaces.keys.results_async:
            # shouldn't ever happen, on async processors we're already directed to the third party
            # site on the final checkout step, all interaction with an async processor are based on processor
            # adapter specific callback views.
            pass
        elif result is interfaces.keys.results_success:
            order_manager = component.getUtility( interfaces.IOrderManager )
            order_manager.store( self.order )
            self.order.finance_workflow.fireTransition("authorize")
            # kill the cart after we create the order
            component.getUtility( interfaces.IShoppingCartUtility ).destroy( self.context )
            return None
        else:
            self.order.finance_workflow.fireTransition('reviewing-declined')
            return  result

