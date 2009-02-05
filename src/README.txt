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
