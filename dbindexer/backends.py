from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.db.models.sql.constants import JOIN_TYPE, LHS_ALIAS, LHS_JOIN_COL, \
    TABLE_NAME, RHS_JOIN_COL
from djangotoolbox.fields import ListField

class BaseResolver(object):
    def __init__(self):
        # mapping from lookups to indexes
        self.index_map = {}
        # mapping from column names to field names
        self.column_to_name = {}
        
    ''' API called by resolver''' 
    
    def create_index(self, lookup):
        field_to_index = self.get_field_to_index(lookup.model, lookup.field_name)
        
        if not field_to_index:
            return 
        
        index_field = lookup.get_field_to_add(field_to_index)        
        config_field = index_field.item_field if \
            isinstance(index_field, ListField) else index_field  
        if hasattr(field_to_index, 'max_length') and \
                isinstance(config_field, models.CharField):
            config_field.max_length = field_to_index.max_length
            
        lookup.model.add_to_class(lookup.index_name, index_field)
        self.index_map[lookup] = index_field
        self.add_column_to_name(lookup.model, lookup.field_name)

    def convert_query(self, query):
        '''Converts a database saving query.'''
        
        for lookup in self.index_map.keys():
            if not lookup.model == query.model:
                continue
            
            position = self.get_query_position(query, lookup)
            if position is None:
                return
            
            value = self.get_value(lookup.model, lookup.field_name, query)
            value = lookup.convert_value(value)
            query.values[position] = (self.get_index(lookup), value)
    
    def convert_filter(self, query, filters, child, index):
        constraint, lookup_type, annotation, value = child
        field_name = self.column_to_name.get(constraint.field.column)
        if field_name and constraint.field is not None and \
                constraint.alias == query.table_map[query.model._meta.db_table][0]:
            for lookup in self.index_map.keys():
                if lookup.matches_filter(query.model, field_name, lookup_type,
                                         value):
                    self._convert_filter(lookup, query, filters, child, index)
                
    ''' helper methods '''
    
    def _convert_filter(self, lookup, query, filters, child, index):
        constraint, lookup_type, annotation, value = child
        lookup_type, value = lookup.convert_lookup(value, lookup_type)
        constraint.field = query.get_meta().get_field(lookup.index_name)
        constraint.col = constraint.field.column
        child = constraint, lookup_type, annotation, value
        filters.children[index] = child
    
    def get_field_to_index(self, model, field_name):
        try:
            return model._meta.get_field(field_name)
        except:
            return None
    
    def get_value(self, model, field_name, query):
        field_to_index = self.get_field_to_index(model, field_name)
        for index, (query_field, value) in enumerate(query.values[:]):
            if field_to_index == query_field:
                return value
        raise FieldDoesNotExist('Cannot find field in query.')
    
    def add_column_to_name(self, model, field_name):
        column_name = model._meta.get_field(field_name).column
        self.column_to_name[column_name] = field_name
    
    def get_index(self, lookup):
        return self.index_map[lookup]
    
    def get_query_position(self, query, lookup):
        for index, (field, query_value) in enumerate(query.values[:]):
            if field is self.get_index(lookup):
                return index
        return None

def unref_alias(query, alias):
        table_name = query.alias_map[alias][TABLE_NAME]
        query.alias_refcount[alias] -= 1
        if query.alias_refcount[alias] < 1:
            # Remove all information about the join
            del query.alias_refcount[alias]
            del query.join_map[query.rev_join_map[alias]]
            del query.rev_join_map[alias]
            del query.alias_map[alias]
            query.table_map[table_name].remove(alias)
            if len(query.table_map[table_name]) == 0:
                del query.table_map[table_name]
            query.used_aliases.discard(alias)

class PKNullFix(BaseResolver):
    '''
        Django doesn't generate correct code for ForeignKey__isnull.
        It becomes a JOIN with pk__isnull which won't work on nonrel DBs,
        so we rewrite the JOIN here.
    '''
    def convert_filter(self, query, filters, child, index):
        constraint, lookup_type, annotation, value = child
        if constraint.field is not None and lookup_type == 'isnull' and \
                        isinstance(constraint.field, models.ForeignKey):
            self.fix_fk_null_filter(query, constraint)
            
    def unref_alias(self, query, alias):
        unref_alias(query, alias)
            
    def fix_fk_null_filter(self, query, constraint):
        alias = constraint.alias
        table_name = query.alias_map[alias][TABLE_NAME]
        lhs_join_col = query.alias_map[alias][LHS_JOIN_COL]
        rhs_join_col = query.alias_map[alias][RHS_JOIN_COL]
        if table_name != constraint.field.rel.to._meta.db_table or \
                rhs_join_col != constraint.field.rel.to._meta.pk.column or \
                lhs_join_col != constraint.field.column:
            return
        next_alias = query.alias_map[alias][LHS_ALIAS]
        if not next_alias:
            return
        self.unref_alias(query, alias)
        alias = next_alias
        constraint.col = constraint.field.column
        constraint.alias = alias
    
    def create_index(self, lookup):
        pass
    
    def convert_query(self, query):
        pass

# TODO: JOIN backend should be configurable per field i.e. in-memory or immutable
class JOINResolver(BaseResolver):
    def create_index(self, lookup):
        if '__' in lookup.field_name:
            BaseResolver.create_index(self, lookup)
    
    def convert_query(self, query):
        for lookup in self.index_map.keys():
            if lookup.model == query.model and '__' in lookup.field_name:
                BaseResolver.convert_query(self, query)
    
    def convert_filter(self, query, filters, child, index):
        constraint, lookup_type, annotation, value = child
        if constraint.field is None:
            return
        
        column_index = self.get_column_index(query, constraint)
        field_name = self.column_to_name.get(column_index)

        if field_name is None:
            return

        for lookup in self.index_map.keys():
            if lookup.matches_filter(query.model, field_name, lookup_type,
                                     value):
                self.resolve_join(lookup, query, filters, child, index)
    
    def get_field_to_index(self, model, field_name):
        model = self.get_model_chain(model, field_name)[-1]
        field_name = field_name.split('__')[-1]
        return BaseResolver.get_field_to_index(self, model, field_name)
    
    def get_value(self, model, field_name, query):
        pk = BaseResolver.get_value(self, model, field_name.split('__')[0],
                                    query)
        value = None
        if pk is not None:
            value = self.get_target_value(model, field_name, pk)
        return value        
    
    def get_model_chain(self, model, field_chain):
        model_chain = [model, ]
        for value in field_chain.split('__')[:-1]:
            model = model._meta.get_field(value).rel.to
            model_chain.append(model)
        return model_chain
       
    def get_target_value(self, start_model, field_chain, pk):
        fields = field_chain.split('__')
        target_model = start_model._meta.get_field(fields[0]).rel.to
        foreignkey = target_model.objects.all().get(pk=pk)
        for value in fields[1:-1]:
            foreignkey = getattr(foreignkey, value)
        return getattr(foreignkey, fields[-1])
    
    def add_column_to_name(self, model, field_name):
        model_chain = self.get_model_chain(model, field_name)
        column_chain = ''
        field_names = field_name.split('__')
        for model, name in zip(model_chain, field_names):
            column_chain += model._meta.get_field(name).column + '__'
        self.column_to_name[column_chain[:-2]] = field_name
        
    def unref_alias(self, query, alias):
        unref_alias(query, alias)
        
    def get_column_index(self, query, constraint):
        if constraint.field:
            column_chain = constraint.field.column
            alias = constraint.alias
            while alias:
                join = query.alias_map[alias]
                if join[JOIN_TYPE] == 'INNER JOIN':
                    column_chain += '__' + join[LHS_JOIN_COL]
                    alias = query.alias_map[alias][LHS_ALIAS]
                else:
                    alias = None
        return '__'.join(reversed(column_chain.split('__')))

    def resolve_join(self, lookup, query, filters, child, index):
        constraint, lookup_type, annotation, value = child
        if not constraint.field:
            return

        alias = constraint.alias
        while True:
            next_alias = query.alias_map[alias][LHS_ALIAS]
            if not next_alias:
                break
            self.unref_alias(query, alias)
            alias = next_alias
        
        constraint.alias = alias
        BaseResolver._convert_filter(self, lookup, query, filters, child, index)