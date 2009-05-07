"""
 A form action adapter that e-mails input.
"""

__author__  = 'Rob LaRubbio <rob@onenw.org>'
__docformat__ = 'plaintext'


########################
# The formMailerAdapter code and schema borrow heavily
# from PloneFormGen <http://plone.org/products/ploneformgen>
# by Steve McMahon <steve@dcn.org> which borrows heavily 
# from PloneFormMailer <http://plone.org/products/ploneformmailer>
# by Jens Klein and Reinout van Rees.
#
# Author:       Jens Klein <jens.klein@jensquadrat.com>
#
# Copyright:    (c) 2004 by jens quadrat, Klein & Partner KEG, Austria
# Licence:      GNU General Public Licence (GPL) Version 2 or later
#######################

from AccessControl import ClassSecurityInfo

from Products.Archetypes.public import *

from Products.ATContentTypes.content.schemata import finalizeATCTSchema
from Products.ATContentTypes.content.base import registerATCT

from Products.CMFCore.permissions import View, ModifyPortalContent

from Products.Archetypes.utils import DisplayList

#from Products.PloneFormGen.config import *

from Products.PloneFormGen.content.formMailerAdapter import FormMailerAdapter, formMailerAdapterSchema

from getpaid.formgen.config import PROJECTNAME

getPaidFormMailerAdapterSchema = formMailerAdapterSchema.copy()


class GetPaidFormMailerAdapter(FormMailerAdapter):
    """ A form action adapter that will e-mail form input. """

    schema = getPaidFormMailerAdapterSchema
    portal_type = meta_type = 'GetPaidFormMailerAdapter'
    archetype_name = 'GetPaid Mailer Adapter'
    content_icon = 'mailaction.gif'

    security       = ClassSecurityInfo()

    security.declarePrivate('onSuccess')
    def onSuccess(self, fields, REQUEST=None):
        """
        e-mails data.
        """
        import pdb; pdb.set_trace()

        # TODO: cram request into attachment for later use
        
        self.send_form(fields, REQUEST)

    security.declareProtected(View, 'allFieldDisplayList')
    def allFieldDisplayList(self):
        """ returns a DisplayList of all fields """

        import pdb; pdb.set_trace()
        ret = []
        for field in self.fgFieldsDisplayList():
            ret.append(field)

        for f in self.gpFieldsDisplayList():
#            f = (field.getName(), field.widget.label)
            ret.append(field.getName())

        return ret
#        return self.fgFieldsDisplayList()


    def gpFieldsDisplayList(self):
        """ returns display list of fields """

        myFields = []
        for obj in GetPaidFields:
            myFields.append( (obj.getId(), obj.title) )

        return DisplayList( myFields )

    def fieldsDisplayList(self):
        """ returns display list of fields with simple values """

        import pdb; pdb.set_trace()
        ret = []

        foo = self.fgFieldsDisplayList(
            withNone=True,
            noneValue='#NONE#',
            objTypes=(
                'FormSelectionField',
                'FormStringField',
                )
            )
        for field in foo:
            ret.append(field)

        for field in GetPaidFields:
            ret.append(field.getName())

        return ret

#         return self.fgFieldsDisplayList(
#             withNone=True,
#             noneValue='#NONE#',
#             objTypes=(
#                 'FormSelectionField',
#                 'FormStringField',
#                 )
#             )

    security.declareProtected(ModifyPortalContent, 'setShowFields')
    def setShowFields(self, value, **kw):
        """ Reorder form input to match field order """
        # This wouldn't be desirable if the PickWidget
        # retained order.

        import pdb; pdb.set_trace()
        self.showFields = []
        for field in self.fgFields(excludeServerSide=False):
            id = field.getName()
            if id in value:
                self.showFields.append(id)


        for field in GetPaidFields:
            id = field.getName()
            if id in value:
                self.showFields.append(id)

registerATCT(GetPaidFormMailerAdapter, PROJECTNAME)

GetPaidFields = [
    StringField('first_name',
        widget=StringWidget(
            description = '',
            description_msgid = "",
            label = u'First Name',
            label_msgid = "",
            i18n_domain = "ploneformgen",
            ),
        ),
    StringField('last_name',
        widget=StringWidget(
            description = '',
            description_msgid = "",
            label = u'Last Name',
            label_msgid = "",
            i18n_domain = "ploneformgen",
            ),
        ),
     ]

#         # First Name
#         fixedRows.append(FixedRow(keyColumn="form_field",
#                                   initialData={"form_field" : "First Name", 
#                                                "field_path" : "contact_information,first_name",
#                                                "sf_field" : ""}))
#         # Last Name
#         fixedRows.append(FixedRow(keyColumn="form_field",
#                                   initialData={"form_field" : "Last Name", 
#                                                "field_path" : "contact_information,last_name",
#                                                "sf_field" : ""}))
