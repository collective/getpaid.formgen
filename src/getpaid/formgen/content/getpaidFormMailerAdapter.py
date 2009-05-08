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

from Products.PloneFormGen.content.fields import *
from Products.PloneFormGen.content.ya_gpg import gpg

from Products.PloneFormGen.content.formMailerAdapter import FormMailerAdapter, formMailerAdapterSchema

from getpaid.formgen.config import PROJECTNAME

# Get Paid events
import zope
from getpaid.core.interfaces import workflow_states, IShoppingCartUtility
from zope.app.component.hooks import getSite
from zope.app.annotation.interfaces import IAnnotations

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

        attachments = self.get_form_attachments(fields, REQUEST)

        all_fields = [f for f in fields
            if not (f.isLabel() or f.isFileField()) and not (getattr(self, 'showAll', True) and f.getServerSide())]

        # which form fields should we show?
        if getattr(self, 'showAll', True):
            live_fields = all_fields 
        else:
            live_fields = \
                [f for f in all_fields
                   if f.fgField.getName() in getattr(self, 'showFields', ())]

        if not getattr(self, 'includeEmpties', True):
            all_fields = live_fields
            live_fields = []
            for f in all_fields:
                value = f.htmlValue(request)
                if value and value != 'No Input':
                    live_fields.append(f)
                
        formFields = []
        for field in live_fields:
            formFields.append( (field.title, field.htmlValue(REQUEST)) )

        # which getpaid fields should we show?
        getPaidFields = []
        if getattr(self, 'showAll', True):
            getPaidFields = GetPaidFields 
        else:
            getPaidFields = \
                [f for f in GetPaidFields
                   if f[0] in getattr(self, 'showFields', ())]

        scu = zope.component.getUtility(IShoppingCartUtility)
        cart = scu.get(self, create=True)

        if (cart == None):
            logger.info("Unable to get cart")
        else:
            # I need to get the name of this adapter so users
            # can add multiple without them conflicting
            annotation = IAnnotations(cart)
            annotation["getpaid.formgen.mailer.added"] = 1
            annotation["getpaid.formgen.mailer.allFields"] = formFields
            annotation["getpaid.formgen.mailer.attachments"] = attachments
            annotation["getpaid.formgen.mailer.getPaidFields"] = getPaidFields

        self.send_form(allFields, REQUEST, getPaidFields=GetPaidFields)

    security.declarePrivate('getMailBodyTypeDefault')
    def getMailBodyTypeDefault(self):
        """ Get default mail body type from our tool """
        
        return DEFAULT_MAILTEMPLATE_BODY

    # Todo implement this to pull attachments out of the annotation
    def get_attachments(self, fields, request):
        """Return all attachments that were uploaded in form
           and stored in an annotation
        """
        scu = zope.component.getUtility(IShoppingCartUtility)
        cart = scu.get(self, create=True)

        attachments = []
        if (cart == None):
            logger.info("Unable to get cart")
        else:
            annotation = IAnnotations(cart)
            if "getpaid.formgen.mailer.attachments" in annotation:
                attachments = annotation["getpaid.formgen.mailer.attachments"]

        return attachments

    def get_form_attachments(self, fields, request):
        """Return all attachments uploaded in form.
        """

        from ZPublisher.HTTPRequest import FileUpload

        attachments = []

        for field in fields:
            if field.isFileField():
                file = request.form.get('%s_file' % field.__name__, None)
                if file and isinstance(file, FileUpload) and file.filename != '':
                    file.seek(0) # rewind
                    data = file.read()
                    filename = file.filename
                    mimetype, enc = guess_content_type(filename, data, None)
                    attachments.append((filename, mimetype, enc, data))
        return attachments

    security.declarePrivate('get_mail_body')
    def get_mail_body(self, fields, **kwargs):
        """Returns the mail-body with footer.
        """

        import pdb; pdb.set_trace()

        bodyfield = self.getField('body_pt')
        
        # pass both the bare_fields (fgFields only) and full fields.
        # bare_fields for compatability with older templates,
        # full fields to enable access to htmlValue
        body = bodyfield.get(self, formFields=fields, **kwargs)

        if isinstance(body, unicode):
            body = body.encode(self.getCharset())

        keyid = getattr(self, 'gpg_keyid', None)
        encryption = gpg and keyid

        if encryption:
            bodygpg = gpg.encrypt(body, keyid)
            if bodygpg.strip():
                body = bodygpg

        return body

    security.declareProtected(View, 'allFieldDisplayList')
    def allFieldDisplayList(self):
        """ returns a DisplayList of all fields """

        ret = []
        for field in self.fgFieldsDisplayList():
            ret.append(field)

        for f in GetPaidFields:
            ret.append(f[0])

        return ret
#        return self.fgFieldsDisplayList()


    def fieldsDisplayList(self):
        """ returns display list of fields with simple values """

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

        ret.append(GETPAID_EMAIL_FIELD)

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

        self.showFields = []
        for field in self.fgFields(excludeServerSide=False):
            id = field.getName()
            if id in value:
                self.showFields.append(id)


        for field in GetPaidFields:
            id = field[0]
            if id in value:
                self.showFields.append(id)

registerATCT(GetPaidFormMailerAdapter, PROJECTNAME)

GETPAID_EMAIL_FIELD = u'Email'

GetPaidFields = (
    (u'First Name', ''),
    (u'Last Name', ''),
    (u'Phone Number', ''),
    (GETPAID_EMAIL_FIELD, ''), 
    (u'Contact Allowed', ''), 
    (u'Email Format Preference', ''),
    (u'Billing Address Street', ''),
    (u'Billing Address City', ''),
    (u'Billing Address Country', ''),
    (u'Billing Address State', ''),
    (u'Billing Address Zip', ''),
    (u'Shipping Address Street', ''),
    (u'Shipping Address City', ''),
    (u'Shipping Address Country', ''),
    (u'Shipping Address State', ''),
    (u'Shipping Address Zip', ''),
    (u'Order Id', ''),
    (u'Order Creation Date', ''),
    (u'Order Total', ''),
    (u'Order Transaction Id', ''),
    (u'CC Last 4', ''),
    (u'Line Item Quantity', ''),
    (u'Line Item Id', ''),
    (u'Line Item Name', ''),
    (u'Line Item Product Code', ''),
    (u'Line Item Item Cost', ''),
    (u'Total Line Item Cost', ''),
    (u'Line Item Item Description', ''),
    )
    
DEFAULT_MAILTEMPLATE_BODY = \
"""<html xmlns="http://www.w3.org/1999/xhtml">

  <head><title></title></head>

  <body>
    <p tal:content="here/getBody_pre | nothing" />
    <dl>
        <tal:block repeat="field options/formFields">
            <dt tal:content="python:field[0]"/>
            <dt tal:content="python:field[1]"/>
        </tal:block>
    </dl>
    <dl>
        <tal:block repeat="field options/getPaidFields">
            <dt tal:content="python:field[0]"/>
            <dt tal:content="python:field[1]"/>
        </tal:block>
    </dl>
    <p tal:content="here/getBody_post | nothing" />
    <pre tal:content="here/getBody_footer | nothing" />
  </body>
</html>
"""
