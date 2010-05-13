""" 
Action for PloneFormGen that helps you getpaid.
"""

__author__  = 'Daniel Holth <dholth@fastmail.fm>'
__docformat__ = 'plaintext'

import logging

from AccessControl import ClassSecurityInfo
from Acquisition import aq_parent
from zope import component
import zope.component

from AccessControl import getSecurityManager
from Products.Archetypes import atapi
from Products.Archetypes.public import StringField, SelectionWidget, \
    DisplayList, Schema, StringWidget, BooleanField, BooleanWidget
from Products.ATContentTypes.content.schemata import finalizeATCTSchema
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import getToolByName

from Products.DataGridField import DataGridField, DataGridWidget
from Products.DataGridField.SelectColumn import SelectColumn
from Products.DataGridField.FixedColumn import FixedColumn
from Products.DataGridField.DataGridField import FixedRow

from Products.PloneFormGen.interfaces import IPloneFormGenField
from getpaid.core import interfaces as GPInterfaces
import getpaid.core

from Products.PloneFormGen.content.actionAdapter import \
    FormActionAdapter, FormAdapterSchema
from Products.PloneFormGen.config import FORM_ERROR_MARKER

from getpaid.formgen.config import PROJECTNAME
from zope.app import zapi
from getpaid.formgen.content.checkout import MakePaymentProcess
from Products.PloneGetPaid.interfaces import IGetPaidManagementOptions, IVariableAmountDonatableMarker
from Products.PloneGetPaid import sessions

logger = logging.getLogger("PloneFormGen")

schema = FormAdapterSchema.copy() + Schema((
    StringField('GPFieldsetType',
                searchable=False,
                required=False,
                mutator='setGPTemplate',
                widget=SelectionWidget(
                       label=u'Get Paid Form Template',
                       i18n_domain = "getpaidpfgadapter",
                       label_msgid = "label_getpaid_template",
                       ),
                vocabulary='getAvailableGetPaidForms'
                ),
                
    BooleanField('useFormAsContinueDestination',
        required=0,
        searchable=0,
        default='0',
        widget=BooleanWidget(
            label="Use form as 'Continue Shopping' destination.",
            description="""
                Check this to instruct the getpaid cart
                to navigate the user back to this form
                if they click 'Continue Shopping' while
                viewing their cart.
                """,
            label_msgid = "label_continue_shopping_text",
            description_msgid = "help_continue_shopping_text",
            i18n_domain = "getpaidpfgadapter",
            ),
        ),

    DataGridField('payablesMap',
         searchable=False,
         required=True,
         columns=('field_path', 'form_field', 'payable_path'),
         fixed_rows = "generateFormFieldRows",
         allow_delete = False,
         allow_insert = False,
         allow_reorder = False,
         widget = DataGridWidget(
             label='Form fields to Payables mapping',
             label_msgid = "label_getpaid_field_map",
             description="""Associate the paths of form fields with payables.""",
             description_msgid = 'help_getpaid_field_map',
             columns= {
                 "field_path" : FixedColumn("Form Fields (path)", visible=False),
                 "form_field" : FixedColumn("Form Fields"),
                 "payable_path" : SelectColumn("Payables", 
                                           vocabulary="buildPayablesList")
             },
             i18n_domain = "getpaid.formgen",
             ),
        ),
    StringField('GPMakePaymentButton',
                default='Make Payment',
                 mutator='setGPSubmit',
                 widget=StringWidget(
                        label=u'Get Paid Payment Button Label',
                        i18n_domain = "getpaidpfgadapter",
                        label_msgid = "label_getpaid_button_label",
                        ))
 
    
))

finalizeATCTSchema(schema, folderish=False, moveDiscussion=False)

class BillingInfo( getpaid.core.options.PropertyBag ):
    title = "Billing Information"

    def __init__(self, context):
        # need a context to be able to get the current available credit
        # cards. purge state afterwards
        self.context = context

    def __getstate__( self ):
        # don't store persistently
        raise RuntimeError("Storage Not Allowed")

BillingInfo = BillingInfo.makeclass( getpaid.core.interfaces.IUserPaymentInformation )

def order_fields(x,y):
    if x[1]>y[1]:
        return 1
    if x[1]<y[1]:
        return -1
    else:
        return 0


def getAvailableCreditCards(self):
    """
    We need the vocabulary for the credit cards in a form that can be understood by pfg
    """
    portal = zapi.getSiteManager()
    portal = getToolByName(portal,'portal_url').getPortalObject()
    manage_options = IGetPaidManagementOptions(portal)
    credit_cards = manage_options.accepted_credit_cards
    available_cards = []
    for card in credit_cards:
        available_cards.append("%s|%s" % (card,card) )
    return tuple(available_cards)
    

class GetpaidPFGAdapter(FormActionAdapter):
    """
    Do PloneGetPaid stuff upon PFG submit.
    """
    schema = schema
    security = ClassSecurityInfo()

    fieldsetType = atapi.ATFieldProperty('GPFieldsetType')    
    makePaymentButton = atapi.ATFieldProperty('GPMakePaymentButton')
    
    portal_type = 'GetpaidPFGAdapter'
    archetype_name = 'Getpaid Adapter'
    content_icon = 'getpaid.gif'

    available_templates = {'One Page Checkout': '_one_page_checkout_init',
                           'Multi item cart add': '_multi_item_cart_add_init' }
    success_callback = None
    
    checkout_fields = {'User Data':[{
                       
        'name':['FormStringField',{'title':u"Your Full Name",
                                   'required':True},10],
        'phone_number':['FormStringField',{'title':u"Phone Number",
                                         'description':u"Only digits allowed - e.g. 3334445555 and not 333-444-5555",
                                           'required':True},11],
        'email':['FormStringField',{'title':u"Email",
                                  'description':u"",
                                    'required':True},11]
        },10],
                       'Billing Address Info':[{
        'bill_first_line':['FormStringField',{'title':u"Address 1",
                                              'required':True},10],
        'bill_second_line':['FormStringField',{'title':u"Address 2"},11],
        'bill_city':['FormStringField',{'title':u"City",
                                        'required':True},12],
        'bill_postal_code':['FormStringField',{'title':u"Zip/Postal Code",
                                               'required':True},13],
        'bill_country':['FormStringField',{'title':u"Country Code",
                                           'description':'Your Country ISO code',
                                               'required':True},14],
        'bill_state':['FormStringField',{'title':u"State Code",
                                         'description':'Your State ISO code',
                                               'required':True},15]
        },20],
                        'Credit Info':[{
        'credit_card_type':['FormSelectionField',{'title':u"Credit Card Type",
                                                  'fgVocabulary':getAvailableCreditCards,
                                                  'required':True},10],
        'name_on_card':['FormStringField',{'title':u"Card Holder Name",
                                         'description':u"Enter the full name, as it appears on the card.",
                                           'required':True},11],
        'credit_card':['FormStringField',{'title':u"Credit Card Number",
                                          'description':u"Only digits allowed - e.g. 4444555566667777 and not 4444-5555-6666-7777 ",
                                          'required':True},12],
        'cc_expiration':['FormDateField',{'title':u"Credit Card Expiration Date",
                                          'required':True},13],
        'cc_cvc':['FormIntegerField',{'title':u"Credit Card Verification Number",
                                      'description':u"For MC, Visa, and DC, this is a 3-digit number on back of the card.  For AmEx, this is a 4-digit code on front of card. ",
                                      'fgmaxlength':4,
                                      'required':True},14],
        },30]
        
                       }

    



    #--------------------------------------------------------------------------#
    #One page checkout methods
    #--------------------------------------------------------------------------#
    def _one_page_checkout_init(self):
        """
        We add all the required fields for getpaid checkout
        TODO: Find a way to get ordered fields
        """
        oids = self.keys()
        ordered_keys = [(afieldset,self.checkout_fields[afieldset][1]) for afieldset in self.checkout_fields.keys()]
        ordered_keys.sort(order_fields)
        ordered_keys = [ordered_key[0] for ordered_key in ordered_keys] # just lazyness to refactor the rest of the method
        
        for frameset in ordered_keys:
            if frameset in oids:
                return
            self.invokeFactory('FieldsetFolder',frameset)
            frame_folder = self[frameset]
            frame_folder.setTitle(frameset)
            ordered_fields = [(fld,self.checkout_fields[frameset][0][fld][2]) for fld in self.checkout_fields[frameset][0].keys()]
            ordered_fields.sort(order_fields)
            ordered_fields = [ordered_key[0] for ordered_key in ordered_fields]
            fs_oids = frame_folder.keys()
            
            for field in ordered_fields:
                if not field in fs_oids:
                    aField = self.checkout_fields[frameset][0][field]
                    frame_folder.invokeFactory(aField[0],field)
                    obj = frame_folder[field]
                    obj.fgField.__name__ = field
                    attribute_list = aField[1]
                    for attr in attribute_list.keys():
                        if hasattr(obj,"set%s" % attr.capitalize()):
                            #A little dirty but apparently calling the method does more
                            #than just setting the value (I will use my it's 2 AM card here)
                            if callable(attribute_list[attr]):
                                getattr(obj,"set%s" % attr.capitalize())(attribute_list[attr](self))
                            else:
                                getattr(obj,"set%s" % attr.capitalize())(attribute_list[attr])                                
                        else:
                            if callable(attribute_list[attr]):
                                obj.getField(attr).set(obj,attribute_list[attr](self))
                            else:
                                obj.getField(attr).set(obj,attribute_list[attr])
                    if 'required' in attribute_list:
                        obj.fgField.required = True

        self.success_callback = "_one_page_checkout_success"

    def _one_page_checkout_success(self, fields, REQUEST=None):
        """
        this process is quite like the regular one except it will use a disposable cart
        """
        portal = zapi.getSiteManager()
        portal = getToolByName(portal,'portal_url').getPortalObject()
        adapters = self.getSchemaAdapters()
        cartKey = "multishot:%s" % aq_parent(self).title
        shopping_cart = component.getUtility(GPInterfaces.IShoppingCartUtility).get(portal, key=cartKey)
        
        #The split is because of the fields inside fieldsets that are presented as a "fieldset,field" string
        form_payable = dict((p['field_path'].split(',')[-1], p['payable_path']) for p in self.payablesMap if p['payable_path'])
        parent_node = self.getParentNode()
        has_products = 0
        error_fields = {}
        for field in fields:
            field_item_factory = zope.component.queryMultiAdapter((shopping_cart, field),
                getpaid.core.interfaces.ILineItemFactory)
            if field_item_factory is not None:
                field_item_factory.create()
                has_products += 1
            if field.getId() in form_payable:
                try:

                    content = parent_node.unrestrictedTraverse(form_payable[field.getId()], None)                        

                    if content is not None:

                        if IVariableAmountDonatableMarker.providedBy(content):
                            arg = float(REQUEST.form.get(field.fgField.getName()))
                        else:
                            arg = int(REQUEST.form.get(field.fgField.getName()))

                        if arg > 0:
                            has_products += 1
                            try:
                                item_factory = zope.component.getMultiAdapter((shopping_cart, content),
                                    getpaid.core.interfaces.ILineItemFactory)
                                item_factory.create(arg)
                            except zope.component.ComponentLookupError:
                                pass
                        elif arg < 0 :
                            error_fields[field.getId()] = "The value for this field is not allowed"
                except KeyError:
                    pass
                except ValueError:
                    error_fields[field.getId()] = "The value for this field is not allowed"
            else:
                for adapter in adapters.values():
                    adapter_fields = zope.schema.getFields(adapter.schema)
                    if field.getId() in adapter_fields.keys():
                        setattr(adapter,field.getId(),REQUEST.form.get(field.fgField.getName()))
        
        if error_fields:
            error_fields.update({FORM_ERROR_MARKER:'Some of the values were incorrect'})
            return error_fields
        if has_products == 0:
            return {FORM_ERROR_MARKER:'There are no products in the order'}
        
        checkout_process = MakePaymentProcess(portal, adapters) 
        result = checkout_process(shopping_cart)

        # I only want this cart to stick around for this submission of the form
        # so destroy it to make sure it doesn't hang around
        scu = component.getUtility(GPInterfaces.IShoppingCartUtility)
        scu.destroy(portal, key=cartKey)

        if result:
            return {FORM_ERROR_MARKER:'%s' % result}
        next_url = self.getNextURL(checkout_process.order, portal)
        if next_url is not None:
            REQUEST.response.redirect(next_url)

    #--------------------------------------------------------------------------#
    #Multi item cart add methods
    #--------------------------------------------------------------------------#

    def _multi_item_cart_add_init(self):
        self.success_callback = "_multi_item_cart_add_success"        

                    
    def _multi_item_cart_add_success(self, fields, REQUEST=None):
        scu = zope.component.getUtility(getpaid.core.interfaces.IShoppingCartUtility)
        cart = scu.get(self, create=True)
        form_payable = dict((p['field_path'], p['payable_path']) for p in self.payablesMap if p['payable_path'])
        parent_node = self.getParentNode()

        formFolder = aq_parent(self)
        formFolderPath = formFolder.getPhysicalPath()
        for field in fields:
            field_item_factory = zope.component.queryMultiAdapter((cart, field),
                getpaid.core.interfaces.ILineItemFactory)
            if field_item_factory is not None:
                field_item_factory.create()
            
            fieldId = ",".join(field.getPhysicalPath()[len(formFolderPath):])
            if fieldId in form_payable:
                try:
                    content = parent_node.unrestrictedTraverse(form_payable[fieldId], None)

                    if content is not None:
                        if IVariableAmountDonatableMarker.providedBy(content):
                            arg = float(REQUEST.form.get(field.fgField.getName()))
                        else:
                            arg = int(REQUEST.form.get(field.fgField.getName()))

                        if arg > 0:
                            try:
                                item_factory = zope.component.getMultiAdapter((cart, content),
                                    getpaid.core.interfaces.ILineItemFactory)
                                item_factory.create(arg)
                            except zope.component.ComponentLookupError:
                                pass
                except KeyError:
                    pass
                except ValueError:
                    pass

    #--------------------------------------------------------------------------#
    #Helper methods
    #--------------------------------------------------------------------------#
    
    def getSchemaAdapters(self):
        adapters = {}
        portal = zapi.getSiteManager()
        portal = getToolByName(portal,'portal_url').getPortalObject()
        user = getSecurityManager().getUser()
        formSchemas = component.getUtility(GPInterfaces.IFormSchemas)
        #persistent sections
        for section in ('contact_information', 'billing_address', 'shipping_address'):
            interface = formSchemas.getInterface(section)
            adapter = component.queryAdapter(user,interface)
            if adapter is None:
                adapter = formSchemas.getBagClass(section)()
            adapters[interface]=adapter
        #non persistent sections
        adapters[formSchemas.getInterface('payment')] = formSchemas.getBagClass('payment')(portal)
        return adapters

    def onSuccess(self, fields, REQUEST=None):
        """
        Will call the on success method according to the chosen template
        """

        result = getattr(self,self.success_callback)(fields, REQUEST)

        # This needs to occur after we add the item to our cart since
        # doing that sets came_from_url to the item
        if getattr(self, 'useFormAsContinueDestination', False):
            sessions.set_came_from_url(aq_parent(self))

        return result
    
    def setGPTemplate(self, template):
        """
        This sets the template for each kind of form
        """
        if template:
            self.getField('GPFieldsetType').set(self,template)
            getattr(self,self.available_templates[template])()

    def setGPSubmit(self, submit_legend):
        """
        This sets the chosen submit button legend
        """
        if submit_legend:
            self.makePaymentButton = submit_legend
            self.setSubmitLabel(submit_legend)

    def updateFieldsData(self, fieldData):
        for fields in fieldData:
            if not 'payable_path' in fields.keys():
                return

            if fields['payable_path']:
                #There should not be more than one level of recursion
                local_widget_name = fields['field_path'].split("-->")
                if len(local_widget_name) > 1:
                    widget = self[local_widget_name[0]][local_widget_name[1]]
                else:
                    widget = self[local_widget_name[0]]
                    
                parent_node = self.getParentNode()
                content = parent_node.restrictedTraverse(fields['payable_path'], None)
                
                payable = GPInterfaces.IPayable(content)    
                if payable.price:
                    title = content.title + " : $%0.2f" % (payable.price)
                else:
                    title = content.title
                description = content.description

                widget.setTitle(title)
                widget.setDescription(description)
                
        
    security.declareProtected(ModifyPortalContent, 'generateFormFieldRows')
    def generateFormFieldRows(self):
        """This method returns a list of rows for the field mapping
           ui. One row is returned for each field in the form folder.
        """
        fixedRows = []
        
        for formFieldTitle, formFieldPath in self._getIPloneFormGenFieldsPathTitlePair():
            logger.debug("creating mapper row for %s" % formFieldTitle)
            fixedRows.append(FixedRow(keyColumn="form_field",
                                      initialData={"form_field" : formFieldTitle, 
                                                   "field_path" : formFieldPath,
                                                   "sf_field" : ""}))
        return fixedRows

    def _getIPloneFormGenFieldsPathTitlePair(self):
        formFolder = aq_parent(self)
        formFolderPath = formFolder.getPhysicalPath()
        formFieldTitles = []
        
        for formField in formFolder.objectIds():
            fieldObj = getattr(formFolder, formField)
            if IPloneFormGenField.providedBy(fieldObj):
                formFieldTitles.append((fieldObj.Title().strip(),
                                        ",".join(fieldObj.getPhysicalPath()[len(formFolderPath):])))
        
            # can we also inspect further down the chain
            if fieldObj.isPrincipiaFolderish:
                # since nested folders only go 1 level deep
                # a non-recursive approach approach will work here
                for subFormField in fieldObj.objectIds():
                    subFieldObj = getattr(fieldObj, subFormField)
                    if IPloneFormGenField.providedBy(subFieldObj):
                        # we append a list in this case
                        formFieldTitles.append(("%s --> %s" % (fieldObj.Title().strip(),
                                                               subFieldObj.Title().strip()),
                                                ",".join(subFieldObj.getPhysicalPath()[len(formFolderPath):])))
        
        return formFieldTitles

    def getNextURL(self, order, context):
        """
        Borrowed from GetPaid this will redirect on submit according to the
        result of the operation
        """
        state = order.finance_state
        f_states = GPInterfaces.workflow_states.order.finance
        base_url = context.absolute_url()
        if not 'http://' in base_url:
            base_url = base_url.replace("https://", "http://")

        if state in (f_states.CANCELLED,
                     f_states.CANCELLED_BY_PROCESSOR,
                     f_states.PAYMENT_DECLINED):
            return base_url + '/@@getpaid-cancelled-declined'

    def getAvailableGetPaidForms(self):
        """
        We will provide a 'vocabulary' with the predefined form templates available
        It is not possible for the moment to do any kind of form without restriction
        """
        
        available_template_list = DisplayList()
        for field in self.available_templates.keys():
            available_template_list.add( field, field )
        return available_template_list


    def buildPayablesList(self):
        """
        Creates a list with the payable marked items on our store
        """
        portal_catalog = getToolByName(self, 'portal_catalog')
        portal_url = getToolByName(self, 'portal_url')
        portal_path = '/'.join(portal_url.getPortalObject().getPhysicalPath())
        buyables = portal_catalog.searchResults(
            dict(object_provides='Products.PloneGetPaid.interfaces.IPayableMarker',
                 path=portal_path))
        stuff = [('', '')]
        for b in buyables:
            o = b.getObject()
            payable = GPInterfaces.IPayable(o)
            if payable.price:
                stuff.append((b.getPath(), o.title + " : %0.2f" % (payable.price)))
            else:
                stuff.append((b.getPath(), o.title))
        display = DisplayList(stuff)
        return display

    
atapi.registerType(GetpaidPFGAdapter, PROJECTNAME)

