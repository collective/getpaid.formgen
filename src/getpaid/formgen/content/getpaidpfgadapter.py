""" 
Action for PloneFormGen that helps you getpaid.
"""

__author__  = 'Daniel Holth <dholth@fastmail.fm>'
__docformat__ = 'plaintext'

import logging

from AccessControl import ClassSecurityInfo
from Acquisition import aq_parent
from zope.interface import classImplements, providedBy
from zope import component
from zope.formlib import form
from DateTime import DateTime
import zope.component

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

from Products.PloneFormGen.content.actionAdapter import \
    FormActionAdapter, FormAdapterSchema

from getpaid.formgen import HAS_PLONE30
from getpaid.formgen.config import PROJECTNAME
from getpaid.formgen import GPFGMessageFactory as _

import getpaid.core

logger = logging.getLogger("PloneFormGen")

schema = FormAdapterSchema.copy() + Schema((
    StringField('GPFieldsetType',
                searchable=0,
                required=1,
                mutator='setGPTemplate',
                widget=SelectionWidget(
                       label='Get Paid Form Template',
                       i18n_domain = "getpaidpfgadapter",
                       label_msgid = "label_getpaid_template",
                       ),
                vocabulary='getAvailableGetPaidForms'
                ),
                
    DataGridField('payablesMap',
         searchable=0,
         required=1,
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
        )
))


class GetpaidPFGAdapter(FormActionAdapter):
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

    # DONT STORED PERSISTENTLY
##     credit_card_type = schema.Choice( title = _(u"Credit Card Type"),
##                                       source = "getpaid.core.accepted_credit_card_types",)

##     credit_card = CreditCardNumber( title = _(u"Credit Card Number"),
##                                     description = _(u"Only digits allowed - e.g. 4444555566667777 and not 4444-5555-6666-7777 "))

##     cc_expiration = schema.Date( title = _(u"Credit Card Expiration Date"),
##                                     description = _(u"Select month and year"))

##     cc_cvc = schema.TextLine(title = _(u"Credit Card Verfication Number"),
##                              description = _(u"For MC, Visa, and DC, this is a 3-digit number on back of the card.  For AmEx, this is a 4-digit code on front of card. "),
##                              min_length = 3,
##                              max_length = 4)
    ###################################################################

    checkout_fields = {
        'name':['FormStringField',{'title':u"Your Full Name"}],
        'phone_number':['FormStringField',{'title':u"Phone Number",
                                         'description':u"Only digits allowed - e.g. 3334445555 and not 333-444-5555"}],
        'email':['FormStringField',{'title':u"Email",
                                  'description':u"Contact Information"}],
        'bill_first_line':['FormStringField',{'title':u"Address 1"}],
        'bill_second_line':['FormStringField',{'title':u"Address 1"}],
        'bill_city':['FormStringField',{'title':u"City"}],
        'bill_postal_code':['FormStringField',{'title':u"Zip/Postal Code"}],
        'name_on_card':['FormStringField',{'title':u"Card Holder Name",
                                         'description':u"Enter the full name, as it appears on the card. "}],
        
                       }
    
    def initializeArchetype(self, **kwargs):
        """Initialize Private instance variables
        """
        FormActionAdapter.initializeArchetype(self, **kwargs)
        self._fieldsForGPType = {}

    def _one_page_checkout_success( self ):
        pass
    
    def _one_page_checkout_init( self ):
        """
        We add all the required fields for getpaid checkout
        """
        oids = self.objectIds()
        for field in self.checkout_fields:
            if field not in oids:
                aField = self.checkout_fields[field]
                self.invokeFactory(aField[0],field)
                obj = self[field]
                obj.fgField.__name__ = field
                attribute_list = aField[1]
                for attr in attribute_list.keys():
                    obj.getField(attr).set(obj,attribute_list[attr])
                if 'required' in attribute_list:
                    obj.fgField.required = True

        self.success_callback = self._one_page_checkout_success
                    
    def _multi_item_cart_add_success(self):
        pass
    
    def _multi_item_cart_add_init(self):
        self.success_callback = self._multi_item_cart_add_success
    
    def setGPTemplate(self, template):
        """
        This will call the initialization methods for each template
        """
        if template:
            getattr(self,self.available_templates[template])()
        
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
        buyables = portal_catalog.searchResults(
            dict(object_provides='Products.PloneGetPaid.interfaces.IPayableMarker',
                 path='/Plone/'))
        stuff = [('', '')]
        stuff.extend((p.getPath(), p.getObject().title) for p in (b for b in buyables))
        display = DisplayList(stuff)        
        return display
    
    def onSuccess(self, fields, REQUEST=None):
##         scu = zope.component.getUtility(getpaid.core.interfaces.IShoppingCartUtility)
##         cart = scu.get(self, create=True)
##         portal_catalog = getToolByName(self, 'portal_catalog')
##         buyables = portal_catalog.searchResults(
##             dict(object_provides='Products.PloneGetPaid.interfaces.IBuyableMarker',
##                 path=self.text))
##         for b in (b.getObject() for b in buyables):
##             item_factory = \
##                 zope.component.getMultiAdapter( (cart, b), 
##                     getpaid.core.interfaces.ILineItemFactory )
##             lineitem = item_factory.create(0)
        return {'name_on_card':'Invalid name'}
    
registerATCT(GetpaidPFGAdapter, PROJECTNAME)

