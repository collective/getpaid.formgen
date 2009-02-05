getpaid.formgen Package Readme
=========================

Overview
--------

PloneGetPaid♡PloneFormGen

Link PloneFormGen with PloneGetPaid so a form can add items or donations
to the GetPaid shopping cart.



Requirements:
-------------
To begin with we need a working Plone instance with PloneGetPaid, PloneFormGen
and DataGridField installed.

Install:
--------
There are two ways of installing getpaid.forgen, if you got it as an egg you
just easy_install it or fetch it with your buildout or else you can copy the
inner formgen from this folder structure to your instance's
/lib/python/getpaid.
After that you will see PloneGetPaid♡PloneFormGen in your plone control
pannel addon product section (you may see two, install whichever you want, 
they are the same thing).
After hitting install you are done, now whenever you create a FormGen folder
you will have as available content types a "GetPaid Adapter" which creates the
required folders for a GetPaid checkout and allows you to map any GetPaid
product on the site to a field on your form.

A few remarks:
------
  * If you are using other adapters (such as salesforce one) please make sure to
    edit and save (even without changes) this one last, because it adds a clause
    to all other present adapters so they execute after it, this avoids comitting
    data of an order that can be rejected.
  * Make sure to remove the default mail adapter from the FormgenForm or you
    could end up sending sensible data by mail by accident.

