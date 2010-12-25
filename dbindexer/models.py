# Load the siteconf module
from django.conf import settings
from django.utils.importlib import import_module
SITECONF_MODULE = getattr(settings, 'DBINDEXER_SITECONF', settings.ROOT_URLCONF)
import_module(SITECONF_MODULE)
