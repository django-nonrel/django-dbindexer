from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.db.models.sql.constants import JOIN_TYPE, LHS_ALIAS, LHS_JOIN_COL, \
    TABLE_NAME, RHS_JOIN_COL
from django.utils.tree import Node
from djangotoolbox.fields import ListField
from .lookups import StandardLookup

OR = 'OR'

# TODO: optimize code
class BaseResolver(object):
    def __init__(self):
        # mapping from lookups to indexes
        self.index_map = {}
        # mapping from column names to field names
        self.column_to_name = {}

    ''' API called by resolver'''

    def create_index(self, lookup):
        field_to_index = self.get_field_to_index(lookup.model, lookup.field_name)

        # backend doesn't now how to handle this index definition
        if not field_to_index:
            return

        index_field = lookup.get_field_to_add(field_to_index)
        config_field = index_field.item_field if \
            isinstance(index_field, ListField) else index_field
        if field_to_index.max_length is not None and \
                isinstance(config_field, models.CharField):
            config_field.max_length = field_to_index.max_length

        if isinstance(field_to_index,
            (models.DateField, models.DateTimeField, models.TimeField)):
            if field_to_index.auto_now or field_to_index.auto_now_add:
                raise ImproperlyConfigured('\'auto_now\' and \'auto_now_add\' '
                    'on %s.%s is not supported by dbindexer.' %
                    (lookup.model._meta.object_name, lookup.field_name))

        # don't install a field if it already exists
        try:
            lookup.model._meta.get_field(self.index_name(lookup))
        except:
            lookup.model.add_to_class(self.index_name(lookup), index_field)
            self.index_map[lookup] = index_field
            self.add_column_to_name(lookup.model, lookup.field_name)
        else:
            # makes dbindexer unit test compatible
            if lookup not in self.index_map:
                self.index_map[lookup] = lookup.model._meta.get_field(
                    self.index_name(lookup))
                self.add_column_to_name(lookup.model, lookup.field_name)

    def convert_insert_query(self, query):
        '''Converts a database saving query.'''

        for lookup in self.index_map.keys():
            self._convert_insert_query(query, lookup)

    def _convert_insert_query(self, query, lookup):
        if not lookup.model == query.model:
            return

        position = self.get_query_position(query, lookup)
        if position is None:
            return

        value = self.get_value(lookup.model, lookup.field_name, query)

        if isinstance(value, list):
            for i in range(0, len(value)):
                setattr(query.objs[i], lookup.index_name, lookup.convert_value(value[i]))
        else:
            try:
                setattr(query.objs[0], lookup.index_name, lookup.convert_value(value))
            except ValueError, e:
                '''
                If lookup.index_name is a foreign key field, we need to set the actual
                referenced object, not just the id.  When we try to set the id, we get an
                exception.
                '''
                field_to_index = self.get_field_to_index(lookup.model, lookup.field_name)

                # backend doesn't now how to handle this index definition
                if not field_to_index:
                    raise Exception('Unable to convert insert query because of unknown field'
                        ' %s.%s' % (lookup.model._meta.object_name, lookup.field_name))

                index_field = lookup.get_field_to_add(field_to_index)
                if isinstance(index_field, models.ForeignKey):
                    setattr(query.objs[0], '%s_id' % lookup.index_name, lookup.convert_value(value))
                else:
                    raise

    def convert_filters(self, query):
        self._convert_filters(query, query.where)

    ''' helper methods '''

    def _convert_filters(self, query, filters):
        for index, child in enumerate(filters.children[:]):
            if isinstance(child, Node):
                self._convert_filters(query, child)
                continue

            self.convert_filter(query, filters, child, index)

    def convert_filter(self, query, filters, child, index):
        constraint, lookup_type, annotation, value = child

        if constraint.field is None:
            return

        field_name = self.column_to_name.get(constraint.field.column)
        if field_name and constraint.alias == \
                query.table_map[query.model._meta.db_table][0]:
            for lookup in self.index_map.keys():
                if lookup.matches_filter(query.model, field_name, lookup_type,
                                         value):
                    new_lookup_type, new_value = lookup.convert_lookup(value,
                                                                       lookup_type)
                    index_name = self.index_name(lookup)
                    self._convert_filter(query, filters, child, index,
                                         new_lookup_type, new_value, index_name)

    def _convert_filter(self, query, filters, child, index, new_lookup_type,
                        new_value, index_name):
        constraint, lookup_type, annotation, value = child
        lookup_type, value = new_lookup_type, new_value
        constraint.field = query.get_meta().get_field(index_name)
        constraint.col = constraint.field.column
        child = constraint, lookup_type, annotation, value
        filters.children[index] = child

    def index_name(self, lookup):
        return lookup.index_name

    def get_field_to_index(self, model, field_name):
        try:
            return model._meta.get_field(field_name)
        except:
            return None

    def get_value(self, model, field_name, query):
        field_to_index = self.get_field_to_index(model, field_name)

        if field_to_index in query.fields:
            values = []
            for obj in query.objs:
                value = field_to_index.value_from_object(obj)
                values.append(value)
            if len(values):
                return values
        raise FieldDoesNotExist('Cannot find field in query.')

    def add_column_to_name(self, model, field_name):
        column_name = model._meta.get_field(field_name).column
        self.column_to_name[column_name] = field_name

    def get_index(self, lookup):
        return self.index_map[lookup]

    def get_query_position(self, query, lookup):
        for index, field in enumerate(query.fields):
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
        query.tables.remove(alias)
        query.table_map[table_name].remove(alias)
        if len(query.table_map[table_name]) == 0:
            del query.table_map[table_name]
        query.used_aliases.discard(alias)

class FKNullFix(BaseResolver):
    '''
        Django doesn't generate correct code for ForeignKey__isnull.
        It becomes a JOIN with pk__isnull which won't work on nonrel DBs,
        so we rewrite the JOIN here.
    '''

    def create_index(self, lookup):
        pass

    def convert_insert_query(self, query):
        pass

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

class ConstantFieldJOINResolver(BaseResolver):
    def create_index(self, lookup):
        if '__' in lookup.field_name:
            super(ConstantFieldJOINResolver, self).create_index(lookup)

    def convert_insert_query(self, query):
        '''Converts a database saving query.'''

        for lookup in self.index_map.keys():
            if '__' in lookup.field_name:
                self._convert_insert_query(query, lookup)

    def convert_filter(self, query, filters, child, index):
        constraint, lookup_type, annotation, value = child
        field_chain = self.get_field_chain(query, constraint)

        if field_chain is None:
            return

        for lookup in self.index_map.keys():
            if lookup.matches_filter(query.model, field_chain, lookup_type,
                                     value):
                self.resolve_join(query, child)
                new_lookup_type, new_value = lookup.convert_lookup(value,
                                                                   lookup_type)
                index_name = self.index_name(lookup)
                self._convert_filter(query, filters, child, index,
                                     new_lookup_type, new_value, index_name)

    def get_field_to_index(self, model, field_name):
        model = self.get_model_chain(model, field_name)[-1]
        field_name = field_name.split('__')[-1]
        return super(ConstantFieldJOINResolver, self).get_field_to_index(model,
            field_name)

    def get_value(self, model, field_name, query):
        value = super(ConstantFieldJOINResolver, self).get_value(model,
                                    field_name.split('__')[0],
                                    query)

        if isinstance(value, list):
            value = value[0]
        if value is not None:
            value = self.get_target_value(model, field_name, value)
        return value

    def get_field_chain(self, query, constraint):
        if constraint.field is None:
            return

        column_index = self.get_column_index(query, constraint)
        return self.column_to_name.get(column_index)

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

        if isinstance(foreignkey._meta.get_field(fields[-1]), models.ForeignKey):
            return getattr(foreignkey, '%s_id' % fields[-1])
        else:
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
                join = query.alias_map.get(alias)
                if join and join[JOIN_TYPE] == 'INNER JOIN':
                    column_chain += '__' + join[LHS_JOIN_COL]
                    alias = query.alias_map[alias][LHS_ALIAS]
                else:
                    alias = None
        return '__'.join(reversed(column_chain.split('__')))

    def resolve_join(self, query, child):
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
class InMemoryJOINResolver(ConstantFieldJOINResolver):
    def __init__(self):
        self.field_chains = []
        super(InMemoryJOINResolver, self).__init__()

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
            super(ConstantFieldJOINResolver, self).create_index(lookup)

    def convert_insert_query(self, query):
        super(ConstantFieldJOINResolver, self).convert_insert_query(query)

    def _convert_filters(self, query, filters):
        # or queries are not supported for in-memory-JOINs
        if self.contains_OR(query.where, OR):
            return

        # start with the deepest JOIN level filter!
        all_filters = self.get_all_filters(filters)
        all_filters.sort(key=lambda item: self.get_field_chain(query, item[1][0]) and \
                         -len(self.get_field_chain(query, item[1][0])) or 0)

        for filters, child, index in all_filters:
            # check if convert_filter removed a given child from the where-tree
            if not self.contains_child(query.where, child):
                continue
            self.convert_filter(query, filters, child, index)

    def convert_filter(self, query, filters, child, index):
        constraint, lookup_type, annotation, value = child
        field_chain = self.get_field_chain(query, constraint)

        if field_chain is None:
            return

        if '__' not in field_chain:
            return super(ConstantFieldJOINResolver, self).convert_filter(query,
                filters, child, index)

        pks = self.get_pks(query, field_chain, lookup_type, value)
        self.resolve_join(query, child)
        self._convert_filter(query, filters, child, index, 'in',
                             (pk for pk in pks), field_chain.split('__')[0])

    def tree_contains(self, filters, to_find, func):
        result = False
        for child in filters.children[:]:
            if func(child, to_find):
                result = True
                break
            if isinstance(child, Node):
                result = self.tree_contains(child, to_find, func)
                if result:
                    break
        return result

    def contains_OR(self, filters, or_):
        return self.tree_contains(filters, or_,
            lambda c, f: isinstance(c, Node) and c.connector == f)

    def contains_child(self, filters, to_find):
        return self.tree_contains(filters, to_find, lambda c, f: c is f)

    def get_all_filters(self, filters):
        all_filters = []
        for index, child in enumerate(filters.children[:]):
            if isinstance(child, Node):
                all_filters.extend(self.get_all_filters(child))
                continue

            all_filters.append((filters, child, index))
        return all_filters

    def index_name(self, lookup):
        # use another index_name to avoid conflicts with lookups defined on the
        # target model which are handled by the BaseBackend
        return lookup.index_name + '_in_memory_join'

    def get_pks(self, query, field_chain, lookup_type, value):
        model_chain = self.get_model_chain(query.model, field_chain)

        first_lookup = {'%s__%s' %(field_chain.rsplit('__', 1)[-1],
                                   lookup_type): value}
        self.combine_with_same_level_filter(first_lookup, query, field_chain)
        pks = model_chain[-1].objects.all().filter(**first_lookup).values_list(
            'id', flat=True)

        chains = [field_chain.rsplit('__', i+1)[0]
                  for i in range(field_chain.count('__'))]
        lookup = {}
        for model, chain in reversed(zip(model_chain[1:-1], chains[:-1])):
            lookup.update({'%s__%s' %(chain.rsplit('__', 1)[-1], 'in'):
                           (pk for pk in pks)})
            self.combine_with_same_level_filter(lookup, query, chain)
            pks = model.objects.all().filter(**lookup).values_list('id', flat=True)
        return pks

    def combine_with_same_level_filter(self, lookup, query, field_chain):
        lookup_updates = {}
        field_chains = self.get_all_field_chains(query, query.where)

        for chain, child in field_chains.items():
            if chain == field_chain:
                continue
            if field_chain.rsplit('__', 1)[0] == chain.rsplit('__', 1)[0]:
                lookup_updates ['%s__%s' %(chain.rsplit('__', 1)[1], child[1])] \
                    = child[3]

                self.remove_child(query.where, child)
                self.resolve_join(query, child)
                # TODO: update query.alias_refcount correctly!
        lookup.update(lookup_updates)

    def remove_child(self, filters, to_remove):
        ''' Removes a child object from filters. If filters doesn't contain
            children afterwoods, filters will be removed from its parent. '''

        for child in filters.children[:]:
            if child is to_remove:
                self._remove_child(filters, to_remove)
                return
            elif isinstance(child, Node):
                self.remove_child(child, to_remove)

            if hasattr(child, 'children') and not child.children:
                self.remove_child(filters, child)

    def _remove_child(self, filters, to_remove):
        result = []
        for child in filters.children[:]:
            if child is to_remove:
                continue
            result.append(child)
        filters.children = result

    def get_all_field_chains(self, query, filters):
        ''' Returns a dict mapping from field_chains to the corresponding child.'''

        field_chains = {}
        all_filters = self.get_all_filters(filters)
        for filters, child, index in all_filters:
            field_chain = self.get_field_chain(query, child[0])
            # field_chain can be None if the user didn't specified an index for it
            if field_chain:
                field_chains[field_chain] = child
        return field_chains
