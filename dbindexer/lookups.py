from django.db import models
from djangotoolbox.fields import ListField
from resolver import resolver
from copy import deepcopy 

import re
regex = type(re.compile(''))

class LookupDoesNotExist(Exception):
    pass

class LookupBase(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        if not isinstance(new_cls.lookup_types, (list, tuple)):
            new_cls.lookup_types = (new_cls.lookup_types, )
        return new_cls 


class ExtraFieldLookup(object):
    '''Default is to behave like an exact filter on an ExtraField.'''
    __metaclass__ = LookupBase
    lookup_types = 'exact'
    
    def __init__(self, model=None, field_name=None, lookup_def=None,
            field_to_add=models.CharField(max_length=500, editable=False,
                                          null=True)):
        self.field_to_add = field_to_add
        self.contribute(model, field_name, lookup_def)
        
    def contribute(self, model, field_name, lookup_def):
        self.model = model
        self.field_name = field_name
        self.lookup_def = lookup_def
            
    @property
    def index_name(self):
        return 'idxf_%s_l_%s' % (self.field_name, self.lookup_types[0])
    
    def convert_lookup(self, value, annotation):
        return 'exact', value
    
    def convert_value(self, value):
        return value
        
    def matches_filter(self, model, field_name, lookup_type, value):
        return self.model == model and lookup_type in self.lookup_types \
            and field_name == self.field_name
    
    @classmethod
    def matches_lookup_def(cls, lookup_def):
        if lookup_def in cls.lookup_types:
            return True
        return False

class DateLookup(ExtraFieldLookup):
    def __init__(self, *args, **kwargs):
        defaults = {'field_to_add': models.IntegerField(editable=False, null=True)}
        defaults.update(kwargs)
        ExtraFieldLookup.__init__(self, *args, **defaults)
    
    def convert_lookup(self, value, annotation):
        return 'exact', value

class Day(DateLookup):
    lookup_types = 'day'
    
    def convert_value(self, value):
        return value.day

class Month(DateLookup):
    lookup_types = 'month'
    
    def convert_value(self, value):
        return value.month

class Year(DateLookup):
    lookup_types = 'year'

    def convert_value(self, value):
        return value.year

class Weekday(DateLookup):
    lookup_types = 'week_day'
    
    def convert_value(self, value):
        return value.isoweekday()

class Contains(ExtraFieldLookup):
    lookup_types = 'contains'

    def __init__(self, *args, **kwargs):
        defaults = {'field_to_add': ListField(models.CharField(500),
                                              editable=False, null=True)
        }
        defaults.update(kwargs)
        ExtraFieldLookup.__init__(self, *args, **defaults)
    
    def convert_lookup(self, value, annotation):
        return 'startswith', value

    def convert_value(self, value):
        return self.contains_indexer(value)

    def contains_indexer(self, value):
        # In indexing mode we add all postfixes ('o', 'lo', ..., 'hello')
        result = []
        if value:
            result.extend([value[count:] for count in range(len(value))])
        return result

class Icontains(Contains):
    lookup_types = 'icontains'
    
    def convert_lookup(self, value, annotation):
        return 'startswith', value.lower()

    def convert_value(self, value):
        return [val.lower() for val in Contains.convert_value(self, value)]

class Iexact(ExtraFieldLookup):
    lookup_types = 'iexact'
    
    def convert_lookup(self, value, annotation):
        return 'exact', value.lower()
    
    def convert_value(self, value):
        return value.lower()

class Istartswith(ExtraFieldLookup):
    lookup_types = 'istartswith'
    
    def convert_lookup(self, value, annotation):
        return 'startswith', value.lower()

    def convert_value(self, value):
        return value.lower()

class Endswith(ExtraFieldLookup):
    lookup_types = 'endswith'
    
    def convert_lookup(self, value, annotation):
        return 'startswith', value[::-1]

    def convert_value(self, value):
        return value[::-1]

class Iendswith(ExtraFieldLookup):
    lookup_types = 'iendswith'
    
    def convert_lookup(self, value, annotation):
        return 'startswith', value[::-1].lower()

    def convert_value(self, value):
        return value[::-1].lower()

class RegexLookup(ExtraFieldLookup):
    lookup_types = ('regex', 'iregex')
    
    def __init__(self, *args, **kwargs):
        defaults = {'field_to_add': models.NullBooleanField(editable=False,
                                                            null=True) 
        }
        defaults.update(kwargs)
        ExtraFieldLookup.__init__(self, *args, **defaults)        
    
    def contribute(self, model, field_name, lookup_def):
        ExtraFieldLookup.contribute(self, model, field_name, lookup_def)
        if isinstance(lookup_def, regex):
            self.lookup_def = re.compile(lookup_def.pattern, re.S | re.U |
                                         (lookup_def.flags & re.I))
    
    @property
    def index_name(self):
        # TODO: use different naming
        return 'idxf_%s_l_%s' % (self.field_name, self.lookup_def.pattern)

    def is_icase(self):
        return self.lookup_def.flags & re.I
    
    def convert_lookup(self, value, annotation):
        return 'exact', True

    def convert_value(self, value):
        if self.lookup_def.match(value):
            return True
        return False
        
    def matches_filter(self, model, field_name, lookup_type, value):
        return self.model == model and lookup_type == \
                '%sregex' % ('i' if self.is_icase() else '') and \
                value == self.lookup_def.pattern and field_name == self.field_name
    
    @classmethod
    def matches_lookup_def(cls, lookup_def):
        if isinstance(lookup_def, regex):
            return True
        return False 

# used for JOINs
#class StandardLookup(ExtraFieldLookup):
#    def __init__(self):
#        # to get the field type for a JOIN definition
#        self.join_resolver = JOINResolver