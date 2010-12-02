from django.db.models.fields import FieldDoesNotExist

# the backend
class Resolver(object):
	def __init__(self):
		pass
		
	def get_value(self, model, field_name, lookup_type):
		pass
	
class StandardResolver(Resolver):
	def get_value(self, model, field_name, lookup_type):
		try:
			return model._meta.get_field(name)
		except FieldDoesNotExist:
			return None	
			
class JOINResolver(Resolver):
	def get_value(self, model, field_name, lookup_type):
		if field_name.contains('__'):
			value = get_denormalization_value(model, field_name, foreign_key_pk)
		try:
			return model._meta.get_field(name)
		except FieldDoesNotExist:
			return None		
	
	def get_denormalization_value(start_model, index_key, foreignkey_pk):
	    denormalized_model = start_model._meta.get_field(
			index_key.split('__')[0]).rel.to
	    foreignkey = denormalized_model.objects.all().get(pk=foreignkey_pk)
	    for value in index_key.split('__')[1:-1]:
	        foreignkey = getattr(foreignkey, value)
    	return getattr(foreignkey, index_key.split('__')[-1])