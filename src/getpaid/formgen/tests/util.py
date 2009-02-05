import os, sys
import glob

from Globals import package_home
from getpaid.formgen.tests import product_globals

def list_acceptance_doctests():
    home = package_home(product_globals) + "/tests/"
    return [os.path.basename(filename) for filename in
            glob.glob(os.path.sep.join([home, 'test*.txt']))]

