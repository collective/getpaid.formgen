# Adapted from SalesforcePFGAdapter source code.

from getpaid.formgen.config import PROJECTNAME
from getpaid.formgen import HAS_PLONE30

from Products.CMFCore.utils import getToolByName

from StringIO import StringIO

ALLTYPES = ('GetpaidPFGAdapter','GetPaidFormMailerAdapter',)
DEPENDENCIES = ('PloneFormGen','PloneGetPaid','DataGridField')

def install(self):
    out = StringIO()
    
    print >> out, u"Installing dependency products"
    portal_qi = getToolByName(self, 'portal_quickinstaller')
    for depend in DEPENDENCIES:
        if portal_qi.isProductInstallable(depend) and not portal_qi.isProductInstalled(depend):
            portal_qi.installProduct(depend)
    
    print >> out, u"Installing GetpaidPFGAdapter"
    setup_tool = getToolByName(self, 'portal_setup')
    if HAS_PLONE30:
        setup_tool.runAllImportStepsFromProfile(
                "profile-getpaid.formgen:default",
                purge_old=False)
    else:
        pass #raise ValueError(u"Plone >= 3.0 required.")
    print >> out, "Installed types and added to portal_factory via portal_setup"
    
    
    # add the GetpaidPFGAdapter type as an addable type to FormField
    types_tool = getToolByName(self, 'portal_types')
    if 'FormFolder' in types_tool.objectIds():
        allowedTypes = types_tool.FormFolder.allowed_content_types
        
        for f in ALLTYPES:
            if f not in allowedTypes:
                allowedTypes = list(allowedTypes)
                allowedTypes.append(f)
                types_tool.FormFolder.allowed_content_types = allowedTypes
                print >> out, u"Added %s to Form Field allowed_content_types" % f
        
    propsTool = getToolByName(self, 'portal_properties')
    siteProperties = getattr(propsTool, 'site_properties')
    navtreeProperties = getattr(propsTool, 'navtree_properties')

    # Add the field, fieldset, thanks and adapter types to types_not_searched
    # This is not desirable to do with GS because we don't want to maintain a list of 
    # the Portal's types_not_searched and we don't want to overwrite existing settings
    typesNotSearched = list(siteProperties.getProperty('types_not_searched'))
    for f in ALLTYPES:
        if f not in typesNotSearched:
            typesNotSearched.append(f)
    siteProperties.manage_changeProperties(types_not_searched = typesNotSearched)
    print >> out, "Added form fields & adapters to types_not_searched"
    
    # Add the field, fieldset, thanks and adapter types to types excluded from navigation
    # This is not desirable to do with GS because we don't want to maintain a list of 
    # the Portal's metaTypesNotToList and we don't want to overwrite existing settings
    typesNotListed = list(navtreeProperties.getProperty('metaTypesNotToList'))
    for f in ALLTYPES:
        if f not in typesNotListed:
            typesNotListed.append(f)
    navtreeProperties.manage_changeProperties(metaTypesNotToList = typesNotListed)
    print >> out, "Added form fields & adapters to metaTypesNotToList"
    
    print >> out, "Successfully installed %s." % PROJECTNAME
    return out.getvalue()


def uninstall(self):
    out = StringIO()
    
    portal_factory = getToolByName(self,'portal_factory')
    propsTool = getToolByName(self, 'portal_properties')
    siteProperties = getattr(propsTool, 'site_properties')
    navtreeProperties = getattr(propsTool, 'navtree_properties')
    types_tool = getToolByName(self, 'portal_types')
    
    # remove salesforce adapter as a factory type
    factory_types = portal_factory.getFactoryTypes().keys()
    for t in ALLTYPES:
        if t in factory_types:
            factory_types.remove(t)
    portal_factory.manage_setPortalFactoryTypes(listOfTypeIds=factory_types)
    print >> out, "Removed form adapters from portal_factory tool"
    
    # remove salesforce adapter from Form Folder's list of addable types
    if 'FormFolder' in types_tool.objectIds():
        allowedTypes = types_tool.FormFolder.allowed_content_types
        
        for t in ALLTYPES:
            if t in allowedTypes:
                allowedTypes = list(allowedTypes)
                allowedTypes.remove(t)
                types_tool.FormFolder.allowed_content_types = allowedTypes
                print >> out, u"Removed %s from FormFolder's allowedTypes" % t
    
    # remove our types from the portal's list of types excluded from navigation
    typesNotListed = list(navtreeProperties.getProperty('metaTypesNotToList'))
    for f in ALLTYPES:
        if f in typesNotListed:
            typesNotListed.remove(f)
    navtreeProperties.manage_changeProperties(metaTypesNotToList = typesNotListed)
    print >> out, "Removed form adapters from metaTypesNotToList"

    # remove our types from the portal's list of types_not_searched
    typesNotSearched = list(siteProperties.getProperty('types_not_searched'))
    for f in ALLTYPES:
        if f in typesNotSearched:
            typesNotSearched.remove(f)
    siteProperties.manage_changeProperties(types_not_searched = typesNotSearched)
    print >> out, "Removed form adapters from types_not_searched"
    
    print >> out, "\nSuccessfully uninstalled %s." % PROJECTNAME
    return out.getvalue()

