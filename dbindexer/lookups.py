from django.db import models
from djangotoolbox.fields import ListField
from copy import deepcopy

''' Three layers:
1. Adding fields
    Instances of ExtraFieldLookup do add extra fields to the model if needed.
    
2. Saving to extra fields
    Instances of ExtraFieldLookup do ask the resolver to get the value for (a) given
    field name(s) so they can convert it to the desired value (lower() for iexact for example)
    
3. Transform queries
    Instances of ExtraFieldLookup know how to transform a query so that a given query can be 
    executed.
'''

import re
regex = type(re.compile(''))

class LookupDoesNotExist(Exception):
    pass

class ExtraFieldLookup():
    lookup_type = None
    field_to_add = models.CharField(max_length=500, editable=False, null=True)
    
    def __init__(self, model=None, field_name=None):
        self.contribute(model, field_name)
        
    def contribute(self, model, field_name):
        self.model = model
        self.field_name = field_name
        self.column_name = None
        if model and field_name:
            self.column_name = model._meta.get_field(self.field_name).column

    @property
    def index_name(self):
        return 'idxf_%s_l_%s' % (self.column_name, self.lookup_type)

    def create_index(self):
        index_field = deepcopy(self.field_to_add)
        field = self.model._meta.get_field(self.field_name)
        if hasattr(field, 'max_length'):
            index_field.max_length = field.max_length
        self.model.add_to_class(self.index_name, index_field)
        
    @classmethod
    def matches_lookup_def(cls, lookup_def):
        if lookup_def == lookup_type:
            return True
        return False

class DateLookup(ExtraFieldLookup):
    field_to_add = models.IntegerField(editable=False, null=True)
    
    @classmethod
    def convert_lookup(cls, value, annotation):
        return 'exact', value

class Day(DateLookup):
    lookup_type = 'day'

    @classmethod
    def convert_value(cls, value):
        return value.day

class Month(DateLookup):
    lookup_type = 'month'

    @classmethod
    def convert_value(cls, value):
        return value.month

class Year(DateLookup):
    lookup_type = 'year'

    @classmethod
    def convert_value(cls, value):
        return value.year

class Weekday(DateLookup):
    lookup_type = 'week_day'

    @classmethod
    def convert_value(cls, value):
        return value.isoweekday()

class Contains(ExtraFieldLookup):
    lookup_type = 'contains'
    field_to_add = ListField(models.CharField(500), editable=False, null=True)
    
    def create_index(self):
        index_field = deepcopy(self.field_to_add)
        field = self.model._meta.get_field(self.field_name)
        if hasattr(field, 'max_length'):
            index_field.item_field.max_length = field.max_length
        self.model.add_to_class(self.index_name, index_field)
    
    @classmethod
    def convert_lookup(cls, value, annotation):
        return 'startswith', value

    @classmethod
    def convert_value(cls, value):
        return cls.contains_indexer(value)

    @classmethod
    def contains_indexer(cls, value):
        # In indexing mode we add all postfixes ('o', 'lo', ..., 'hello')
        result = []
        if value:
            result.extend([value[count:] for count in range(len(value))])
        return result

class Icontains(Contains):
    lookup_type = 'icontains'
    
    @classmethod
    def convert_lookup(cls, value, annotation):
        return 'startswith', value.lower()

    @classmethod
    def convert_value(cls, value):
        return [val.lower() for val in Contains.convert_value(value)]

class Iexact(ExtraFieldLookup):
    lookup_type = 'iexact'
    
    @classmethod
    def convert_lookup(cls, value, annotation):
        return 'exact', value.lower()
    
    @classmethod
    def convert_value(cls, value):
        return value.lower()

class Istartswith(ExtraFieldLookup):
    lookup_type = 'istartswith'
    
    @classmethod
    def convert_lookup(cls, value, annotation):
        return 'startswith', value.lower()

    @classmethod
    def convert_value(cls, value):
        return value.lower()

class Endswith(ExtraFieldLookup):
    lookup_type = 'endswith'
    
    @classmethod
    def convert_lookup(cls, value, annotation):
        return 'startswith', value[::-1]

    @classmethod
    def convert_value(cls, value):
        return value[::-1]

class Iendswith(ExtraFieldLookup):
    lookup_type = 'iendswith'
    
    @classmethod
    def convert_lookup(cls, value, annotation):
        return 'startswith', value[::-1].lower()

    @classmethod
    def convert_value(cls, value):
        return value[::-1].lower()

class RegexLookup(ExtraFieldLookup):
    lookup_type = ('regex', 'iregex') 
    field_to_add = ListField(models.CharField(max_length=256), editable=False,
                             null=True)
    models_with_extra_field = []
    
    def __init__(self, model, field_name, regex):
        self.regex = re.compile(regex.pattern, re.S | re.U | (regex.flags & re.I))
    
    def create_index(self):
        if model not in self.models_with_extra_field:
            index_field = deepcopy(self.field_to_add)
            self.model.add_to_class(self.index_name, index_field)
            self.models_with_extra_field.append(model)
    
    @classmethod
    def convert_lookup(cls, value, annotation):
        return self.lookup_type == 'regex' and ('exact', ':' + value) or \
            ('exact', 'i:' + value)

    @classmethod
    def convert_value(cls, value):
        return
    
    @classmethod
    def matches_lookup_def(cls, lookup_def):
        if isinstance(lookup_def, regex):
            return True
        return False

# used for JOINs
class StandardLookup(ExtraFieldLookup):
    def __init__(self):
        # to get the field type for a JOIN definition
        self.join_resolver = JOINResolver
        
    
    