""" 
Action for PloneFormGen that helps you getpaid.
"""

__author__  = 'Daniel Holth <dholth@fastmail.fm>'
__docformat__ = 'plaintext'

import logging
from DateTime import DateTime

from AccessControl import ClassSecurityInfo
from Acquisition import aq_parent
from zope.interface import classImplements, providedBy
from zope import component
from zope.formlib import form
from zope.event import notify
import zope.component

from AccessControl import getSecurityManager
from Products.Archetypes import atapi
from Products.Archetypes.public import StringField, SelectionWidget, \
    DisplayList, Schema, ManagedSchema
from Products.ATContentTypes.content.schemata import finalizeATCTSchema
from Products.ATContentTypes.content.base import registerATCT
from Products.CMFCore.permissions import View, ModifyPortalContent
from Products.CMFCore.utils import getToolByName
from Products.validation.config import validation

from Products.DataGridField import DataGridField, DataGridWidget
from Products.DataGridField.SelectColumn import SelectColumn
from Products.DataGridField.FixedColumn import FixedColumn
from Products.DataGridField.DataGridField import FixedRow

from Products.PloneFormGen.interfaces import IPloneFormGenField
from getpaid.core import interfaces as GPInterfaces
import getpaid.core

from Products.PloneFormGen import HAS_PLONE30
from Products.PloneFormGen.content.actionAdapter import \
    FormActionAdapter, FormAdapterSchema
from Products.PloneFormGen.config import FORM_ERROR_MARKER

from getpaid.formgen.config import PROJECTNAME
from getpaid.formgen import GPFGMessageFactory as _
from zope.app import zapi
from getpaid.formgen.content.checkout import MakePaymentProcess, CreateTransientOrder
from Products.PloneGetPaid.interfaces import IGetPaidManagementOptions

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
                
    DataGridField('payablesMap',
         searchable=False,
         required=True,
         schemata='payables mapping',
         columns=('field_path', 'form_field', 'payable_path'),
         fixed_rows = "generateFormFieldRows",
         allow_delete = True,
         allow_insert = True,
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
                mutator='setGPSubmit',)
    
))


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
    

class GetpaidPFGAdapter( FormActionAdapter ):
    """
    Do PloneGetPaid stuff upon PFG submit.
    """
    schema = schema
    security = ClassSecurityInfo()
    
    portal_type = 'GetpaidPFGAdapter'
    archetype_name = 'Getpaid Adapter'
    content_icon = 'getpaid.gif'

    available_templates = {'One Page Checkout': '_one_page_checkout_init',
                           'Multi item cart add': '_multi_item_cart_add_init' }

    success_callback = None

##     bill_country = schema.Choice( title = _(u"Country"),
##                                     vocabulary = "getpaid.countries")
##     bill_state = schema.Choice( title = _(u"State"),
##                                   vocabulary="getpaid.states" )
    ###################################################################

    
    checkout_fields = {'User Data':{
                       
        'name':['FormStringField',{'title':u"Your Full Name",
                                   'required':True}],
        'phone_number':['FormStringField',{'title':u"Phone Number",
                                         'description':u"Only digits allowed - e.g. 3334445555 and not 333-444-5555",
                                           'required':True}],
        'email':['FormStringField',{'title':u"Email",
                                  'description':u"Contact Information",
                                    'required':True}]
        },
                       'Billing Address Info':{
        'bill_first_line':['FormStringField',{'title':u"Address 1",
                                              'required':True}],
        'bill_second_line':['FormStringField',{'title':u"Address 2"}],
        'bill_city':['FormStringField',{'title':u"City",
                                        'required':True}],
        'bill_postal_code':['FormStringField',{'title':u"Zip/Postal Code",
                                               'required':True}]},
                        'Credit Info':{
        'credit_card_type':['FormSelectionField',{'title':u"Credit Card Type",
                                                  'fgVocabulary':getAvailableCreditCards,
                                                  'required':True}],
        'name_on_card':['FormStringField',{'title':u"Card Holder Name",
                                         'description':u"Enter the full name, as it appears on the card.",
                                           'required':True}],
        'credit_card':['FormStringField',{'title':u"Credit Card Number",
                                          'description':u"Only digits allowed - e.g. 4444555566667777 and not 4444-5555-6666-7777 ",
                                          'required':True}],
        'cc_expiration':['FormDateField',{'title':u"Credit Card Expiration Date",
                                          'description':u"Credit Card Expiration Date",
                                          'required':True}],
        'cc_cvc':['FormIntegerField',{'title':u"Credit Card Verfication Number",
                                      'description':u"For MC, Visa, and DC, this is a 3-digit number on back of the card.  For AmEx, this is a 4-digit code on front of card. ",
                                      'fgmaxlength':4,
                                      'required':True}],
        }
        
                       }
    
    def initializeArchetype(self, **kwargs):
        """Initialize Private instance variables
        """
        FormActionAdapter.initializeArchetype(self, **kwargs)
        self._fieldsForGPType = {}

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

    def _one_page_checkout_success(self, fields, REQUEST=None):
        """
        this process is quite like the regular one except it will use a disposable cart
        """
        portal = zapi.getSiteManager()
        portal = getToolByName(portal,'portal_url').getPortalObject()
        adapters = self.getSchemaAdapters()
        shopping_cart = component.getUtility(GPInterfaces.IShoppingCartUtility).get(portal, key="oneshot:bogus")
        
        portal_catalog = getToolByName(self, 'portal_catalog')
        form_payable = dict((p['field_path'], p['payable_path']) for p in self.payablesMap if p['payable_path'])
        parent_node = self.getParentNode()
        for field in fields:
            if field.getId() in form_payable:
                try:
                    quantity = int(REQUEST.form.get(field.fgField.getName()))
                    if quantity > 0:
                        content = parent_node.restrictedTraverse(form_payable[field.getId()], None)                        
                        if content is not None:
                            try:
                                item_factory = zope.component.getMultiAdapter((shopping_cart, content),
                                    getpaid.core.interfaces.ILineItemFactory)
                                item_factory.create(quantity)
                            except zope.component.ComponentLookupError, e:
                                import pdb ; pdb.set_trace()
                except KeyError, e:
                    pass
                except ValueError, e:
                    pass
            else:
                for adapter in adapters.values():
                    adapter_fields = zope.schema.getFields(adapter.schema)
                    if field.getId() in adapter_fields.keys():
                        setattr(adapter,field.getId(),REQUEST.form.get(field.fgField.getName()))
                        
                
                
        checkout_process = MakePaymentProcess(portal, adapters) 
        result = checkout_process(shopping_cart)
        if result:
            return {FORM_ERROR_MARKER:'%s' % result}
        
        
    
    def _one_page_checkout_init(self):
        """
        We add all the required fields for getpaid checkout
        TODO: Find a way to get ordered fields
        """
        oids = self.objectIds()
        for frameset in self.checkout_fields.keys():
            self.invokeFactory('FieldsetFolder',frameset)
            frame_folder = self[frameset]
            frame_folder.setTitle(frameset)
            for field in self.checkout_fields[frameset].keys():
                if field not in oids:
                    aField = self.checkout_fields[frameset][field]
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
                    
    def _multi_item_cart_add_success(self, fields, REQUEST=None):
        scu = zope.component.getUtility(getpaid.core.interfaces.IShoppingCartUtility)
        cart = scu.get(self, create=True)
        portal_catalog = getToolByName(self, 'portal_catalog')
        form_payable = dict((p['field_path'], p['payable_path']) for p in self.payablesMap if p['payable_path'])
        parent_node = self.getParentNode()
        for field in fields:
            if field.getId() in form_payable:
                try:
                    quantity = int(REQUEST.form.get(field.fgField.getName()))
                    if quantity > 0:
                        content = parent_node.restrictedTraverse(form_payable[field.getId()], None)                        
                        if content is not None:
                            try:
                                item_factory = zope.component.getMultiAdapter((cart, content),
                                    getpaid.core.interfaces.ILineItemFactory)
                                item_factory.create(quantity)
                            except zope.component.ComponentLookupError, e:
                                import pdb ; pdb.set_trace()
                except KeyError, e:
                    pass
                except ValueError, e:
                    pass
    
    def _multi_item_cart_add_init(self):
        self.success_callback = "_multi_item_cart_add_success"
    
    def setGPTemplate(self, template):
        """
        This will call the initialization methods for each template
        """
        if template:
            getattr(self,self.available_templates[template])()

    def setGPSubmit(self, submit_legend):
        """
        This will call the initialization methods for each template
        """
        if submit_legend:
            self.setSubmitLabel(submit_legend)
        
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
            stuff.append((b.getPath(), o.title + " : %0.2f" % (payable.price)))
        display = DisplayList(stuff)        
        return display


    def onSuccess(self, fields, REQUEST=None):
        result = getattr(self,self.success_callback)(fields, REQUEST)
        return result
        # return {'name_on_card':'Invalid Name'}
    

registerATCT(GetpaidPFGAdapter, PROJECTNAME)

