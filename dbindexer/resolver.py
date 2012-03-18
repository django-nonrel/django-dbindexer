from django.conf import settings
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured

class Resolver(object):
    def __init__(self):
        self.backends = []
        self.load_backends(getattr(settings, 'DBINDEXER_BACKENDS',
                               ('dbindexer.backends.BaseResolver',
                                'dbindexer.backends.FKNullFix')))

    def load_backends(self, backend_paths):
        for backend in backend_paths:
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

    def convert_insert_query(self, query):
        for backend in self.backends:
            backend.convert_insert_query(query)

resolver = Resolver()
