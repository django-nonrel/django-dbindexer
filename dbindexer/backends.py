from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.db.models.sql.constants import JOIN_TYPE, LHS_ALIAS, LHS_JOIN_COL, \
    TABLE_NAME, RHS_JOIN_COL
from django.utils.tree import Node
from djangotoolbox.fields import ListField
from dbindexer.lookups import StandardLookup

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
            
        # don't install a field if it already exists
        try:
            lookup.model._meta.get_field(self.index_name(lookup))
        except:
            lookup.model.add_to_class(self.index_name(lookup), index_field)
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
    
    def convert_filters(self, query, filters):
        model = query.model
        for index, child in enumerate(filters.children[:]):
            if isinstance(child, Node):
                self.convert_filters(query, child)
                continue

            self.convert_filter(query, filters, child, index)
    
    def convert_filter(self, query, filters, child, index):
        constraint, lookup_type, annotation, value = child
        field_name = self.column_to_name.get(constraint.field.column)
        if field_name and constraint.field is not None and \
                constraint.alias == query.table_map[query.model._meta.db_table][0]:
            for lookup in self.index_map.keys():
                if lookup.matches_filter(query.model, field_name, lookup_type,
                                         value):
                    new_lookup_type, new_value = lookup.convert_lookup(value,
                                                                       lookup_type)
                    index_name = self.index_name(lookup)
                    self._convert_filter(query, filters, child, index,
                                         new_lookup_type, new_value, index_name)
                
    ''' helper methods '''
    
    def index_name(self, lookup):
        return lookup.index_name
    
    def _convert_filter(self, query, filters, child, index, new_lookup_type,
                        new_value, index_name):
        constraint, lookup_type, annotation, value = child
        lookup_type, value = new_lookup_type, new_value
        constraint.field = query.get_meta().get_field(index_name)
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
                self.resolve_join(query, filters, child, index)
                new_lookup_type, new_value = lookup.convert_lookup(value,
                                                                   lookup_type)
                index_name = self.index_name(lookup)
                self._convert_filter(query, filters, child, index,
                                     new_lookup_type, new_value, index_name)
    
    def get_field_to_index(self, model, field_name):
        model = self.get_model_chain(model, field_name)[-1]
        field_name = field_name.split('__')[-1]
        return BaseResolver.get_field_to_index(self, model, field_name)
    
    def get_value(self, model, field_name, query):
        value = BaseResolver.get_value(self, model, field_name.split('__')[0],
                                    query)
        if value is not None:
            value = self.get_target_value(model, field_name, value)
        return value        
    
    def get_model_chain(self, model, field_chain):
        model_chain = [model, ]
        for value in field_chain.split('__')[:-1]:
            model = model._meta.get_field(value).rel.to
            model_chain.append(model)
        return model_chain
       
    def get_target_value(self, start_model, field_chain, pk):
        fields = field_chain.split('__')
        foreign_key = start_model._meta.get_field(fields[0])
        
        if not foreign_key.rel:
            # field isn't a related one, so return the value itself
            return pk
        
        target_model = foreign_key.rel.to
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

    def resolve_join(self, query, filters, child, index):
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

# TODO: distinguish in memory joins from standard joins somehow
# add possibility to add additional filters on the to-one side CAUTION: efficient
# only if the paths of the filters to the to-one side are the same (without the last
# field). This can be translated to an and (because paths are the same). With different
# pats the results have to be merged i.e. first follow first path and fetch then follow
# next path and fetch and then merge.
class InMemoryJOINResolver(JOINResolver):
    def create_index(self, lookup):
        if '__' in lookup.field_name:
            field_to_index = self.get_field_to_index(lookup.model, lookup.field_name)
        
            if not field_to_index:
                return 
            
            # save old column_to_name so we can make in memory queries later on 
            self.add_column_to_name(lookup.model, lookup.field_name)
            
            # don't add an extra field for standard lookups!
            if isinstance(lookup, StandardLookup):
                return 
             
            # install lookup on target model
            model = self.get_model_chain(lookup.model, lookup.field_name)[-1]
            lookup.model = model
            lookup.field_name = lookup.field_name.split('__')[-1]
            BaseResolver.create_index(self, lookup)
    
    def index_name(self, lookup):
        # use another index_name to avoid conflicts with lookups defined on the
        # target model which are handled by the BaseBackend
        return lookup.index_name + '_in_memory_join'
    
    def convert_query(self, query):
        BaseResolver.convert_query(self, query)
    
    def convert_filter(self, query, filters, child, index):
        constraint, lookup_type, annotation, value = child
        if constraint.field is None:
            return
        
        column_index = self.get_column_index(query, constraint)
        field_chain = self.column_to_name.get(column_index)

        if field_chain is None:
            return
        
        if '__' not in field_chain:
            return BaseResolver.convert_filter(self, query, filters, child, index)
        
        pks = self.get_pks(query, field_chain, lookup_type, value)
        self.resolve_join(query, filters, child, index)
        # TODO: what happens if pks is empty?
        self._convert_filter(query, filters, child, index, 'in',
                             (pk for pk in pks), field_chain.split('__')[0])
        
    def get_pks(self, query, field_chain, lookup_type, value):
        model_chain = self.get_model_chain(query.model, field_chain)
        field_names = field_chain.split('__')
        first_lookup = {'%s__%s' %(field_names[-1], lookup_type): value}
        pks = model_chain[-1].objects.all().filter(**first_lookup).values_list(
            'id', flat=True)
        
        for model, field_name in reversed(zip(model_chain[1:-1], field_names[1:-1])):
            lookup = {'%s__%s' %(field_name, 'in'):(pk for pk in pks)}
            # TODO: what haens if pks is empty?
            pks = model.objects.all().filter(**lookup)
        return pks