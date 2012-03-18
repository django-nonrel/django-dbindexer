from django.db import models
from djangotoolbox.fields import ListField
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
                 new_lookup='exact', field_to_add=models.CharField(
                 max_length=500, editable=False, null=True)):
        self.field_to_add = field_to_add
        self.new_lookup = new_lookup
        self.contribute(model, field_name, lookup_def)

    def contribute(self, model, field_name, lookup_def):
        self.model = model
        self.field_name = field_name
        self.lookup_def = lookup_def

    @property
    def index_name(self):
        return 'idxf_%s_l_%s' % (self.field_name, self.lookup_types[0])

    def convert_lookup(self, value, lookup_type):
        # TODO: can value be a list or tuple? (in case of in yes)
        if isinstance(value, (tuple, list)):
            value = [self._convert_lookup(val, lookup_type)[1] for val in value]
        else:
            _, value = self._convert_lookup(value, lookup_type)
        return self.new_lookup, value

    def _convert_lookup(self, value, lookup_type):
        return lookup_type, value

    def convert_value(self, value):
        if value is not None:
            if isinstance(value, (tuple, list)):
                value = [self._convert_value(val) for val in value]
            else:
                value = self._convert_value(value)
        return value

    def _convert_value(self, value):
        return value

    def matches_filter(self, model, field_name, lookup_type, value):
        return self.model == model and lookup_type in self.lookup_types \
            and field_name == self.field_name

    @classmethod
    def matches_lookup_def(cls, lookup_def):
        if lookup_def in cls.lookup_types:
            return True
        return False

    def get_field_to_add(self, field_to_index):
        field_to_add = deepcopy(self.field_to_add)
        if isinstance(field_to_index, ListField):
            field_to_add = ListField(field_to_add, editable=False, null=True)
        return field_to_add

class DateLookup(ExtraFieldLookup):
    def __init__(self, *args, **kwargs):
        defaults = {'new_lookup': 'exact',
                    'field_to_add': models.IntegerField(editable=False, null=True)}
        defaults.update(kwargs)
        ExtraFieldLookup.__init__(self, *args, **defaults)

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, value

class Day(DateLookup):
    lookup_types = 'day'

    def _convert_value(self, value):
        return value.day

class Month(DateLookup):
    lookup_types = 'month'

    def _convert_value(self, value):
        return value.month

class Year(DateLookup):
    lookup_types = 'year'

    def _convert_value(self, value):
        return value.year

class Weekday(DateLookup):
    lookup_types = 'week_day'

    def _convert_value(self, value):
        return value.isoweekday()

class Contains(ExtraFieldLookup):
    lookup_types = 'contains'

    def __init__(self, *args, **kwargs):
        defaults = {'new_lookup': 'startswith',
                    'field_to_add': ListField(models.CharField(500),
                                              editable=False, null=True)
        }
        defaults.update(kwargs)
        ExtraFieldLookup.__init__(self, *args, **defaults)

    def get_field_to_add(self, field_to_index):
        # always return a ListField of CharFields even in the case of
        # field_to_index being a ListField itself!
        return deepcopy(self.field_to_add)

    def convert_value(self, value):
        new_value = []
        if isinstance(value, (tuple, list)):
            for val in value:
                new_value.extend(self.contains_indexer(val))
        else:
            new_value = self.contains_indexer(value)
        return new_value

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, value

    def contains_indexer(self, value):
        # In indexing mode we add all postfixes ('o', 'lo', ..., 'hello')
        result = []
        if value:
            result.extend([value[count:] for count in range(len(value))])
        return result

class Icontains(Contains):
    lookup_types = 'icontains'

    def convert_value(self, value):
        return [val.lower() for val in Contains.convert_value(self, value)]

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, value.lower()

class Iexact(ExtraFieldLookup):
    lookup_types = 'iexact'

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, value.lower()

    def _convert_value(self, value):
        return value.lower()

class Istartswith(ExtraFieldLookup):
    lookup_types = 'istartswith'

    def __init__(self, *args, **kwargs):
        defaults = {'new_lookup': 'startswith'}
        defaults.update(kwargs)
        ExtraFieldLookup.__init__(self, *args, **defaults)

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, value.lower()

    def _convert_value(self, value):
        return value.lower()

class Endswith(ExtraFieldLookup):
    lookup_types = 'endswith'

    def __init__(self, *args, **kwargs):
        defaults = {'new_lookup': 'startswith'}
        defaults.update(kwargs)
        ExtraFieldLookup.__init__(self, *args, **defaults)

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, value[::-1]

    def _convert_value(self, value):
        return value[::-1]

class Iendswith(Endswith):
    lookup_types = 'iendswith'

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, value[::-1].lower()

    def _convert_value(self, value):
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
        return 'idxf_%s_l_%s' % (self.field_name,
                                 self.lookup_def.pattern.encode('hex'))

    def is_icase(self):
        return self.lookup_def.flags & re.I

    def _convert_lookup(self, value, lookup_type):
        return self.new_lookup, True

    def _convert_value(self, value):
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

class StandardLookup(ExtraFieldLookup):
    ''' Creates a copy of the field_to_index in order to allow querying for
        standard lookup_types on a JOINed property. '''
    # TODO: database backend can specify standardLookups
    lookup_types = ('exact', 'gt', 'gte', 'lt', 'lte', 'in', 'range', 'isnull')

    @property
    def index_name(self):
        return 'idxf_%s_l_%s' % (self.field_name, 'standard')

    def convert_lookup(self, value, lookup_type):
        return lookup_type, value

    def get_field_to_add(self, field_to_index):
        field_to_add = deepcopy(field_to_index)
        if isinstance(field_to_add, (models.DateTimeField,
                                    models.DateField, models.TimeField)):
            field_to_add.auto_now_add = field_to_add.auto_now = False
        return field_to_add
