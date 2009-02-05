""" 
Action for PloneFormGen that helps you getpaid.

Adapted from an adapter for PloneFormGen that saves submitted form
data to Salesforce.com
"""

__author__  = 'Daniel Holth <dholth@fastmail.fm>'
__docformat__ = 'plaintext'

# Python imports
import logging

# Zope imports
from AccessControl import ClassSecurityInfo
from Acquisition import aq_parent
from zope.interface import classImplements, providedBy
from zope import component
from zope.formlib import form
from DateTime import DateTime
import zope.component

# Plone imports
from Products.Archetypes import atapi
from Products.Archetypes.public import StringField, SelectionWidget, \
    DisplayList, Schema, ManagedSchema
from Products.ATContentTypes.content.schemata import finalizeATCTSchema
from Products.ATContentTypes.content.base import registerATCT
from Products.CMFCore.permissions import View, ModifyPortalContent
from Products.CMFCore.utils import getToolByName
from Products.validation.config import validation

# DataGridField
from Products.DataGridField import DataGridField, DataGridWidget
from Products.DataGridField.SelectColumn import SelectColumn
from Products.DataGridField.FixedColumn import FixedColumn
from Products.DataGridField.DataGridField import FixedRow

# Interfaces
from Products.PloneFormGen.interfaces import IPloneFormGenField

# GetPaid imports
from getpaid.core import interfaces as GPInterfaces

# PloneFormGen imports
from Products.PloneFormGen import HAS_PLONE30
from Products.PloneFormGen.content.actionAdapter import \
    FormActionAdapter, FormAdapterSchema

from getpaid.formgen.config import PROJECTNAME
from getpaid.formgen import GPFGMessageFactory as _

import getpaid.core

logger = logging.getLogger("PloneFormGen")

# validation.register(validators.CircularDependencyValidator('CircularDependencyValidator'))

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
                )
    
))


    # StringField('SFObjectType',
    #     searchable=0,
    #     required=1,
    #     default=u'Contact',
    #     mutator='setSFObjectType',
    #     widget=SelectionWidget(
    #         label='Salesforce Object Type',
    #         i18n_domain = "salesforcepfgadapter",
    #         label_msgid = "label_salesforce_type_text",
    #         ),
    #     vocabulary='displaySFObjectTypes',
    #     ),
    # DataGridField('fieldMap',
    #      searchable=0,
    #      required=1,
    #      schemata='field mapping',
    #      columns=('field_path', 'form_field', 'sf_field'),
    #      fixed_rows = "generateFormFieldRows",
    #      allow_delete = False,
    #      allow_insert = False,
    #      allow_reorder = False,
    #      widget = DataGridWidget(
    #          label='Form fields to Salesforce fields mapping',
    #          label_msgid = "label_salesforce_field_map",
    #          description="""The following Form Fields are available\
    #              within your Form Folder. Choose the appropriate \
    #              Salesforce Field for each Form Field.""",
    #          description_msgid = 'help_salesforce_field_map',
    #          columns= {
    #              "field_path" : FixedColumn("Form Fields (path)", visible=False),
    #              "form_field" : FixedColumn("Form Fields"),
    #              "sf_field" : SelectColumn("Salesforce Fields",
    #                                        vocabulary="buildSFFieldOptionList")
    #          },
    #          i18n_domain = "salesforcepfgadapter",
    #          ),
    #     ),
    # DataGridField('dependencyMap',
    #      searchable=0,
    #      required=0,
    #      schemata='field mapping',
    #      columns=('adapter_name', 'adapter_id', 'sf_field'),
    #      fixed_rows = "getLocalSFAdapters",
    #      allow_delete = False,
    #      allow_insert = False,
    #      allow_reorder = False,
    #      widget = DataGridWidget(
    #          label='Configure Parent Adapters',
    #          label_msgid = "label_salesforce_dependency_map",
    #          description="""This form's other Salesforce Adapters are listed below. \
    #             To relate the current adapter's Saleforce record to the Salesforce \
    #             record created by another Salesforce Adapter, select the field that \
    #             relates both records. Note: relationships are made from children \
    #             back to parents.""",
    #          description_msgid = 'help_salesforce_dependency_map',
    #          columns= {
    #              "adapter_name" : FixedColumn("Possible Parent Adapters"),
    #              "adapter_id" : FixedColumn("Possible Parent Adapters (id)", visible=False),
    #              "sf_field" : SelectColumn("Available Field IDs",
    #                                        vocabulary="buildSFFieldOptionList")
    #          },
    #          i18n_domain = "salesforcepfgadapter",
    #          ),
    #      validators = ('CircularDependencyValidator',),
    #      )


# move 'field mapping' schemata before the inherited overrides schemata
#schema = ManagedSchema(schema.copy().fields())
# schema.moveSchemata('field mapping', -1)

# IBillingAddressSchema = Schema((
#     bill_name = schema.TextLine( title = _(u"Full Name"))
#     bill_first_line = schema.TextLine( title = _(u"Address 1"))
#     bill_second_line = schema.TextLine( title = _(u"Address 2"), required=False )
#     bill_city = schema.TextLine( title = _(u"City") )
#     bill_country = schema.Choice( title = _(u"Country"),
#                                     vocabulary = "getpaid.countries")
#     bill_state = schema.Choice( title = _(u"State"),
#                                   vocabulary="getpaid.states" )
#     bill_postal_code = schema.TextLine( title = _(u"Zip/Postal Code"))
#     ))

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


##     bill_country = schema.Choice( title = _(u"Country"),
##                                     vocabulary = "getpaid.countries")
##     bill_state = schema.Choice( title = _(u"State"),
##                                   vocabulary="getpaid.states" )

    checkout_fields = {'bill_name':['FormTextField',{title:u"Full Name"}],
                       'bill_first_line':['FormTextField',{title:u"Address 1"],
                       'bill_second_line':['FormTextField',{title:u"Address 1"],
                       'bill_city':['FormTextField',{title:u"City"],
                       'bill_postal_code':['FormTextField',{title:u"Zop/Postal Code"]  
                       }
    
    def initializeArchetype(self, **kwargs):
        """Initialize Private instance variables
        """
        FormActionAdapter.initializeArchetype(self, **kwargs)
        self._fieldsForGPType = {}

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
                attribute_list = aFile[1]
                for attr in attribute_list:
                    setattr(obj,attr,attirbute_list[attr]
                    

    def _multi_item_cart_add_init( self ):
        pass
    
    def setGPTemplate( self, template ):
        """
        This will call the initialization methods for each template
        """
        if template:
            getattr(self,self.available_templates[sections_group])()
        

    def getAvailableGetPaidForms( self ):
        """
        We will provide a 'vocabulary' with the predefined form templates available
        It is not possible for the moment to do any kind of form without restriction
        """
        
        available_template_list = DisplayList()
        for field in self.available_templates.keys():
            available_template_list.add( field, field )
        return available_template_list
    
    def onSuccess(self, fields, REQUEST=None):
        scu = zope.component.getUtility(getpaid.core.interfaces.IShoppingCartUtility)
        cart = scu.get(self, create=True)
        portal_catalog = getToolByName(self, 'portal_catalog')
        buyables = portal_catalog.searchResults(
            dict(object_provides='Products.PloneGetPaid.interfaces.IBuyableMarker',
                path=self.text))
        for b in (b.getObject() for b in buyables):
            item_factory = \
                zope.component.getMultiAdapter( (cart, b), 
                    getpaid.core.interfaces.ILineItemFactory )
            lineitem = item_factory.create(0)
    
registerATCT(GetpaidPFGAdapter, PROJECTNAME)

# try:
#     from Products.Archetypes.interfaces import IMultiPageSchema
#     classImplements(SalesforcePFGAdapter, IMultiPageSchema)
# except ImportError:
#     pass
