from django.conf import settings
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured

class Resolver(object):
    def __init__(self):
        self.backends = []
        for backend in getattr(settings, 'DBINDEXER_BACKENDS',
                               ('dbindexer.backends.BaseResolver',
                                'dbindexer.backends.FKNullFix')):
                self.backends.append(self.load_backend(backend))

    def load_backend(self, path):
        module_name, attr_name = path.rsplit('.', 1)
        try:
            mod = import_module(module_name)
        except (ImportError, ValueError), e:
            raise ImproperlyConfigured('Error importing backend module %s: "%s"'
                % (module_name, e))
        try:
            return getattr(mod, attr_name)()
        except AttributeError:
            raise ImproperlyConfigured('Module "%s" does not define a "%s" backend'
                % (module_name, attr_name))

    def convert_filters(self, query):
        for backend in self.backends:
            backend.convert_filters(query)

    def create_index(self, lookup):
        for backend in self.backends:
            backend.create_index(lookup)

    def convert_query(self, query):
        for backend in self.backends:
            backend.convert_query(query)

resolver = Resolver()