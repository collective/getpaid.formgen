#GetPaid imports
from Products.PloneGetPaid.interfaces import IGetPaidManagementOptions, ICreateTransientOrder
from getpaid.core import interfaces
from getpaid.core.order import Order

#Local imports
from getpaid.formgen.interfaces import IMakePaymentProcess

#Zope imports
from zope import interface, component
from zope.app import zapi

#Other imports
from cPickle import loads, dumps

class CreateTransientOrder( object ):
    """
    A really transient order
    """
    interface.implements(ICreateTransientOrder)

    def __call__( self, shopping_cart=None ):
        order = Order()

        portal = zapi.getSiteManager()
        if soppping_cart is None:
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
        self.processor = component.getAdapter( context,
                                               interfaces.IPaymentProcessor,
                                               processor_name )
        self.adapters = adapters
        self.order = CreateTransientOrder()
        
    def __call__( self, oneshot=None ):
        """
        If called as oneshot it will not use the site's cart, instead oneshot
        should be the cart to use
        """
        adapters = self.wizard.data_manager.adapters

        shopping_cart = oneshot
        if oneshot is None:
            portal = zapi.getSiteManager()
            shopping_cart = component.getUtility( interfaces.IShoppingCartUtility ).get( portal )
            shopping_cart = loads( dumps( shopping_cart ) )

        order = self.order( shopping_cart )
        order.processor_id = processor_name
        order.finance_workflow.fireTransition( "create" )
        
        # extract data to our adapters
        result = self.processor.authorize( order, self.adapters[formSchemas.getInterface('payment')] )
        if result is interfaces.keys.results_async:
            # shouldn't ever happen, on async processors we're already directed to the third party
            # site on the final checkout step, all interaction with an async processor are based on processor
            # adapter specific callback views.
            pass
        elif result is interfaces.keys.results_success:
            order_manager = component.getUtility( interfaces.IOrderManager )
            order_manager.store( order )
            order.finance_workflow.fireTransition("authorize")
            # kill the cart after we create the order
            component.getUtility( interfaces.IShoppingCartUtility ).destroy( self.context )
            return None
        else:
            order.finance_workflow.fireTransition('reviewing-declined')
            return = result
