from django.db import models
from djangotoolbox.fields import ListField
from copy import deepcopy

class BaseResolver(object):
    def __init__(self):
        self.lookups = []
        
    def get_field_to_index(self, model, field_name):
        try:
            return model._meta.get_field(field_name)
        except:
            raise FieldDoesNotExist('Cannot find field %s in model %s.'
                                % (field_name, model.__name__))
    
    def get_value(self, model, field_name, query):
        field_to_index = self.get_field_to_index(model, field_name)
        for index, (query_field, value) in enumerate(query.values[:]):
            if field_to_index == query_field:
                return value
        raise FieldDoesNotExist('Cannot find field in query.')
    
    def convert_filter(self, query, filters, child, index):
        for lookup in self.lookups:
            if lookup.matches_filter(query, child, index):
                constraint, lookup_type, annotation, value = child
                lookup_type, value = lookup.convert_lookup(value, annotation)
                constraint.field = query.get_meta().get_field(lookup.index_name)
                constraint.col = constraint.field.column
                child = (constraint, lookup_type, annotation, value)
                filters.children[index] = child
    
    def create_index(self, lookup):
        field_to_index = self.get_field_to_index(lookup.model, lookup.field_name)
        # TODO: move index_field out of lookup
        lookup.index_field = deepcopy(lookup.field_to_add)
        
        config_field = lookup.index_field.item_field if \
            isinstance(lookup.index_field, ListField) else lookup.index_field  
        if hasattr(field_to_index, 'max_length') and \
                isinstance(config_field, models.CharField):
            config_field.max_length = field_to_index.max_length
            
        lookup.model.add_to_class(lookup.index_name, lookup.index_field)
        self.lookups.append(lookup)
    
    def get_query_position(self, query):
        for index, (field, query_value) in enumerate(query.values[:]):
            if field is self.index_field:
                return index
        return None
    
            
# TODO: JOIN backend should be configurable per field i.e. in-memory or immutable
class JOINResolver(BaseResolver):
    def get_field_to_index(self, model, field_name):
        try:
            model = self.get_target_model(model)
            field_name = field_name.split('__')[-1]
            return BaseResolver.get_field_to_index(self, model, field_name)
        except:
            raise FieldDoesNotExist('Cannot find field %s in model %s.'
                                % (field_name, model.__name__))
    
    def get_value(self, model, field_name, query):
        pk = BaseResolver.get_value(self, model, field_name.split('__')[0],
                                    query)
        value = self.get_target_value(model, field_name, pk)
        try:
            return model._meta.get_field(name)
        except FieldDoesNotExist:
            return None        
    
    def get_target_model(self, start_model, field_chain):
        target_model = start_model
        for value in field_chain.split('__')[:-1]:
            target_model = denormalized_model._meta.get_field(value).rel.to
        return target_model
       
    def get_target_value(start_model, field_chain, pk):
        fields = field_chain.split('__')
        target_model = start_model._meta.get_field(fields[0]).rel.to
        foreignkey = target_model.objects.all().get(pk=pk)
        for value in fields[1:-1]:
            foreignkey = getattr(foreignkey, value)
        return getattr(foreignkey, fields[-1])