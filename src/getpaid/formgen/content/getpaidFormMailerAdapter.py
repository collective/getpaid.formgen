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

import logging

from AccessControl import ClassSecurityInfo

from Products.Archetypes.public import *
from Products.Archetypes.utils import OrderedDict
from Products.Archetypes.utils import shasattr

from Products.ATContentTypes.content.schemata import finalizeATCTSchema
from Products.ATContentTypes.content.base import registerATCT

from Products.CMFCore.permissions import View, ModifyPortalContent

from Products.Archetypes.utils import DisplayList

from Products.PloneFormGen import dollarReplace

from Products.PloneFormGen.content.fields import *
from Products.PloneFormGen.content.ya_gpg import gpg

from Products.PloneFormGen.content.formMailerAdapter import FormMailerAdapter, formMailerAdapterSchema

from getpaid.formgen.config import PROJECTNAME

from email.Header import Header

# Get Paid events
import zope
from getpaid.core.interfaces import workflow_states, IShoppingCartUtility
from zope.app.component.hooks import getSite
from zope.app.annotation.interfaces import IAnnotations

import copy
from Acquisition import aq_base

logger = logging.getLogger("GetPaidFormMailer")

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

        scu = zope.component.getUtility(IShoppingCartUtility)
        cart = scu.get(self, create=True)

        if (cart == None):
            logger.info("Unable to get cart")
        else:
            # I need to get the name of this adapter so users
            # can add multiple without them conflicting
            annotation = IAnnotations(cart)

            if "getpaid.formgen.mailer.adapters" in annotation:
                adapters = annotation["getpaid.formgen.mailer.adapters"]

                if not self.title in adapters:
                    adapters.append(self.title)
            else:
                adapters = [self.title]

            annotation["getpaid.formgen.mailer.adapters"] = adapters

            annotationKey = "getpaid.formgen.mailer.%s" % self.title

            data = {}
            data['formFields'] = formFields
            data['attachments'] = attachments

            # This is a complete hack and I can't believe it isn't
            # going to come back and break in the future
            # I just need some of the request for my supers
            # implementation.  I can't pickle an aq wrapped object, so
            # I resort to this.  Perhaps it's better to reimplement
            # the code from my super I'm reusing?
            req = {}
            req['form'] = copy.deepcopy(REQUEST.form)
            for key in getattr(self, 'xinfo_headers', []):
                if REQUEST.has_key(key):
                    req[key] = REQUEST[key]

            data['request'] = req

            tmp = copy.copy(aq_base(self))
            data['adapter'] = tmp

            annotation[annotationKey] = data

    security.declarePrivate('_dreplace')
    def _dreplace(self, s):
        _form = getattr(self.REQUEST, 'form', None)
        if _form is None:
            _form = self.REQUEST['form']

        return dollarReplace.DollarVarReplacer(_form).sub(s)

    security.declarePrivate('getMailBodyDefault')
    def getMailBodyDefault(self):
        """ Get default mail body from our tool """
        
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

    # I override this method since I don't have a real request object.
    # I have a dict instead.
    security.declarePrivate('get_header_body_tuple')
    def get_header_body_tuple(self, fields, request,
                              from_addr=None, to_addr=None,
                              subject=None, **kwargs):
        """Return header and body of e-mail as an 3-tuple:
        (header, additional_header, body)

        header is a dictionary, additional header is a list, body is a StringIO

        Keyword arguments:
        request -- (optional) alternate request object to use
        """

        body = self.get_mail_body(fields, **kwargs)

        # fields = self.fgFields()

        # get Reply-To
        reply_addr = None
        if shasattr(self, 'replyto_field'):
            reply_addr = request['form'].get(self.replyto_field, None)

        # get subject header
        nosubject = '(no subject)'
        if shasattr(self, 'subjectOverride') and self.getRawSubjectOverride():
            # subject has a TALES override
            subject = self.getSubjectOverride().strip()
        else:
            subject = getattr(self, 'msg_subject', nosubject)
            subjectField = request['form'].get(self.subject_field, None)
            if subjectField is not None:
                subject = subjectField
            else:
                # we only do subject expansion if there's no field chosen
                subject = dollarReplace.DollarVarReplacer(request['form']).sub(subject)

        # Get From address
        if shasattr(self, 'senderOverride') and self.getRawSenderOverride():
            from_addr = self.getSenderOverride().strip()
        else:
            pprops = getToolByName(self, 'portal_properties')
            site_props = getToolByName(pprops, 'site_properties')
            portal = getToolByName(self, 'portal_url').getPortalObject()
            from_addr = from_addr or site_props.getProperty('email_from_address') or \
                        portal.getProperty('email_from_address')

        # Get To address and full name
        if shasattr(self, 'recipientOverride') and self.getRawRecipientOverride():
            recip_email = self.getRecipientOverride()
        else:
            recip_email = None
            if shasattr(self, 'to_field'):
                recip_email = request['form'].get(self.to_field, None)
            if not recip_email:
                recip_email = self.recipient_email
        recip_email = self._destFormat( recip_email )

        recip_name = self.recipient_name.encode('utf-8')

        # if no to_addr and no recip_email specified, use owner adress if possible.
        # if not, fall back to portal email_from_address.
        # if still no destination, raise an assertion exception.
        if not recip_email and not to_addr:
            ownerinfo = self.getOwner()
            ownerid=ownerinfo.getId()
            pms = getToolByName(self, 'portal_membership')
            userdest = pms.getMemberById(ownerid)
            toemail = userdest.getProperty('email', '')
            if not toemail:
                portal = getToolByName(self, 'portal_url').getPortalObject()
                toemail = portal.getProperty('email_from_address')                
            assert toemail, """
                    Unable to mail form input because no recipient address has been specified.
                    Please check the recipient settings of the PloneFormGen "Mailer" within the
                    current form folder.
                """
            to = '%s <%s>' %(ownerid,toemail)
        else:
            to = to_addr or '%s %s' % (recip_name, recip_email)

        headerinfo = OrderedDict()

        headerinfo['To'] = self.secure_header_line(to)
        headerinfo['From'] = self.secure_header_line(from_addr)
        if reply_addr:
            headerinfo['Reply-To'] = self.secure_header_line(reply_addr)

        # transform subject into mail header encoded string
        portal = getToolByName(self, 'portal_url').getPortalObject()
        email_charset = portal.getProperty('email_charset', 'utf-8')
        msgSubject = self.secure_header_line(subject).encode(email_charset, 'replace')
        msgSubject = str(Header(msgSubject, email_charset))
        headerinfo['Subject'] = msgSubject

        headerinfo['MIME-Version'] = '1.0'

        # CC
        cc_recips = filter(None, self.cc_recipients)
        if cc_recips:
            headerinfo['Cc'] = self._destFormat( cc_recips )

        # BCC
        bcc_recips = filter(None, self.bcc_recipients)
        if shasattr(self, 'bccOverride') and self.getRawBccOverride():
            bcc_recips = self.getBccOverride()
        if bcc_recips:
            headerinfo['Bcc'] = self._destFormat( bcc_recips )

        for key in getattr(self, 'xinfo_headers', []):
            headerinfo['X-%s' % key] = self.secure_header_line(request.get(key, 'MISSING'))

        # return 3-Tuple
        return (headerinfo, self.additional_headers, body)

    security.declareProtected(View, 'allFieldDisplayList')
    def allFieldDisplayList(self):
        """ returns a DisplayList of all fields """

        ret = []
        for field in self.fgFieldsDisplayList():
            ret.append(field)

        return ret


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

        ret.append(EMAIL)

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


registerATCT(GetPaidFormMailerAdapter, PROJECTNAME)

def handleOrderWorkflowTransition( order, event ):

    if order.finance_state == event.destination and event.destination == workflow_states.order.finance.CHARGED:
        annotation = IAnnotations(order.shopping_cart)

        if "getpaid.formgen.mailer.adapters" in annotation:
            adapters = annotation["getpaid.formgen.mailer.adapters"]

            getPaidFields = _getValuesFromOrder(order)
            site = zope.app.component.hooks.getSite()
            for a in adapters:
                annotationKey = "getpaid.formgen.mailer.%s" % a
                data = annotation[annotationKey]

                formFields = data['formFields']
                attachments = data['attachments']
                request = data['request']
                adapter = data['adapter']

                adapter.__of__(site).send_form(formFields, request, getPaidFields=getPaidFields)
            
def _getValuesFromOrder(order):
    ret = {}
    
    import pdb; pdb.set_trace()
    ret[NAME] = order.contact_information.name
    ret[PHONE_NUMBER] = order.contact_information.phone_number
    ret[EMAIL] = order.contact_information.email
    ret[CONTACT_ALLOWED] = order.contact_information.marketing_preference
    ret[EMAIL_PREFERENCE] = order.contact_information.email_html_format
    ret[BILLING_STREET_1] = order.billing_address.bill_first_line
    ret[BILLING_STREET_2] = order.billing_address.bill_second_line
    ret[BILLING_CITY] = order.billing_address.bill_city
    ret[BILLING_COUNTRY] = order.billing_address.bill_country
    ret[BILLING_STATE] = order.billing_address.bill_state    
    ret[BILLING_ZIP] = order.billing_address.bill_postal_code      
    ret[SHIPPING_STREET_1] = order.shipping_address.ship_first_line
    ret[SHIPPING_STREET_2] = order.shipping_address.ship_second_line
    ret[SHIPPING_CITY] = order.shipping_address.ship_city    
    ret[SHIPPING_COUNTRY] = order.shipping_address.ship_country
    ret[SHIPPING_STATE] = order.shipping_address.ship_state      
    ret[SHIPPING_ZIP] = order.shipping_address.ship_postal_code         
    ret[ORDER_ID] = order.order_id
    ret[ORDER_DATE] = order.creation_date.ctime()
    ret[ORDER_TOTAL] = order.getTotalPrice()
    ret[ORDER_TRANSACTION_ID] = order.processor_order_id
    ret[CC_LAST_4] = order.user_payment_info_last4
    ret[ORDER_ITEMS_ARRAY] = []

    for item in order.shopping_cart.items():
        itemDict = {}
        itemDict[ITEM_QTY] = item[1].quantity
        itemDict[ITEM_ID] = item[1].item_id
        itemDict[ITEM_NAME] = item[1].name           
        itemDict[ITEM_PRODUCT_CODE] = item[1].product_code   
        itemDict[ITEM_COST] = item[1].cost           
        itemDict[ITEM_TOTAL_COST] = item[1].cost * item[1].quantity
        itemDict[ITEM_DESC] = item[1].description    

        ret[ORDER_ITEMS_ARRAY].append(itemDict)

    return ret
    
NAME                 = u'Name'
PHONE_NUMBER         = u'Phone Number' 
EMAIL                = u'Email'
CONTACT_ALLOWED      = u'Contact Allowed' 
EMAIL_PREFERENCE     = u'Email Format Preference'
BILLING_STREET_1     = u'Billing Address Street 1'
BILLING_STREET_2     = u'Billing Address Street 2'
BILLING_CITY         = u'Billing Address City'
BILLING_COUNTRY      = u'Billing Address Country'
BILLING_STATE        = u'Billing Address State'
BILLING_ZIP          = u'Billing Address Zip'
SHIPPING_STREET_1    = u'Shipping Address Street 1'
SHIPPING_STREET_2    = u'Shipping Address Street 2'
SHIPPING_CITY        = u'Shipping Address City'
SHIPPING_COUNTRY     = u'Shipping Address Country'
SHIPPING_STATE       = u'Shipping Address State'
SHIPPING_ZIP         = u'Shipping Address Zip'
ORDER_ID             = u'Order Id'
ORDER_DATE           = u'Order Creation Date'
ORDER_TOTAL          = u'Order Total'
ORDER_TRANSACTION_ID = u'Order Transaction Id'
CC_LAST_4            = u'CC Last 4'
ORDER_ITEMS_ARRAY    = u'Items'
ITEM_QTY             = u'Line Item Quantity'
ITEM_ID              = u'Line Item Id'
ITEM_NAME            = u'Line Item Name'
ITEM_PRODUCT_CODE    = u'Line Item Product Code'
ITEM_COST            = u'Line Item Item Cost'
ITEM_TOTAL_COST      = u'Total Line Item Cost'
ITEM_DESC            = u'Line Item Item Description'

GetPaidFields = (
    NAME,
    PHONE_NUMBER,
    EMAIL,
    CONTACT_ALLOWED,
    EMAIL_PREFERENCE,
    BILLING_STREET_1,
    BILLING_STREET_2,
    BILLING_CITY,
    BILLING_COUNTRY,
    BILLING_STATE,
    BILLING_ZIP,
    SHIPPING_STREET_1,
    SHIPPING_STREET_2,
    SHIPPING_CITY,
    SHIPPING_COUNTRY,
    SHIPPING_STATE,
    SHIPPING_ZIP,
    ORDER_ID,
    ORDER_DATE,
    ORDER_TOTAL,
    ORDER_TRANSACTION_ID,
    CC_LAST_4,
    ORDER_ITEMS_ARRAY,
    ITEM_QTY,
    ITEM_ID,
    ITEM_NAME,
    ITEM_PRODUCT_CODE,
    ITEM_COST,
    ITEM_TOTAL_COST,
    ITEM_DESC,
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
        <tal:block define="field options/getPaidFields" tal:repeat="v python:field.keys()">
            <dt tal:content="v"/>
            <dt tal:content="python:field[v]"/>
        </tal:block>
    </dl>
    <p tal:content="here/getBody_post | nothing" />
    <pre tal:content="here/getBody_footer | nothing" />
  </body>
</html>
"""
