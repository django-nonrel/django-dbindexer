from django.db.models.fields import FieldDoesNotExist
from django.conf import settings
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured

class Resolver(object):
	def __init__(self):
		self.backends = []
		self.lookups = []
		for backend in settings.DBINDEXER_BACKENDS:
			self.backends.append(self.load_backend(backend))
	
	def load_backend(self, path):
	    module_name, attr_name = path.rsplit('.', 1)
	    try:
	        mod = import_module(module_name)
	    except (ImportError, ValueError), e:
	        raise ImproperlyConfigured('Error importing backend module %s: "%s"' % (module_name, e))
	    try:
	        cls = getattr(mod, attr_name)
	        return cls()
	    except AttributeError:
	        raise ImproperlyConfigured('Module "%s" does not define a "%s" backend' % (module_name, attr_name))
	
	def get_field_to_index(self, model, field_name):
		for backend in self.backends:
			try:
				return backend.get_field_to_index(model, field_name)
			except:
				continue
		raise FieldDoesNotExist('Cannot find field %s for model %s.'
                                % (field_name, model.__name__))
		
	def get_value(self, model, field_name, query):
		for backend in self.backends:
			try:
				return backend.get_value(model, field_name, query)
			except:
				continue
		raise FieldDoesNotExist('Cannot find field %s for model %s in query.'
                                % (field_name, model.__name__))
	
	def convert_filter(self, query, filters, child, index):
		for backend in self.backends:
			try:
				return backend.convert_filter(query, filters, child, index)
			except:
				continue
			
	def create_index(self, lookup):
		for backend in self.backends:
			backend.lookups.append(lookup)

resolver = Resolver()