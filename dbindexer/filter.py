from django.db import models
from djangotoolbox.fields import ListField
from copy import deepcopy

class ExtraFieldLookup():
    def __init__(self, model=None, field_name=None, lookup_type=None,
            field_to_add=models.CharField(max_length=500, editable=False, null=True)):
        self.model = model
        self.field_name = field_name

        self.column_name = None
        if model and field_name:
            self.column_name = model._meta.get_field(self.field_name).column
            
        self.field_to_add = field_to_add
        self.lookup_type = lookup_type

    def contribute(self, model, field_name):
        self.model = model
        self.field_name = field_name
        if model and field_name:
            self.column_name = model._meta.get_field(self.field_name).column

    @property
    def index_name(self):
        return 'idxf_%s_l_%s' % (self.column_name, self.lookup_type)

    def create_index(self, model):
        index_field = deepcopy(self.field_to_add)
        model.add_to_class(self.index_name, index_field)

    def convert_lookup(self, value, annotation):
        pass

    def convert_value(self, value):
        pass

class DateLookup(ExtraFieldLookup):
    def __init__(self, model, field_name, lookup_type):
        super(ExtraFieldLookup, self).__init__(model, field_name,
            lookup_type, models.IntegerField(editable=False, null=True))

    def convert_lookup(self, value, annotation):
        return 'exact', value

class Day(DateLookup):
    def __init__(self, model, field_name):
        super(DateLookup, self).__init__(model, field_name, 'day')

    def convert_value(self, value):
        return value.day

class Month(DateLookup):
    def __init__(self, model, field_name):
        super(DateLookup, self).__init__(model, field_name, 'month')

    def convert_value(self, value):
        return value.month

class Year(DateLookup):
    def __init__(self, model, field_name):
        super(DateLookup, self).__init__(model, field_name, 'year')

    def convert_value(self, value):
        return value.year

class Weekday(DateLookup):
    def __init__(self, model, field_name):
        super(DateLookup, self).__init__(model, field_name, 'week_day')

    def convert_value(self, value):
        return value.isoweekday()

class RegexFilter(ExtraFieldLookup):
    def __init__(self, model, field_name, regex):
        self.regex = re.compile(regex.pattern, re.S | re.U | (regex.flags & re.I))
        lookup_type = self.regex.flags & re.I and 'iregex' or 'regex'
        super(ExtraFieldLookup, self).__init__(model, field_name,
            lookup_type, ListField(models.CharField(max_length=256),
            editable=False, null=True))

    def create_index(self, model):
        # TODO: only create one list field for all regexes for a given model
        super(ExtraFieldLookup, self).create_index(model)

    def convert_lookup(self, value, annotation):
        return self.lookup_type == 'regex' and ('exact', ':' + value) or \
            ('exact', 'i:' + value)

    def convert_value(self, value):
        return

class Contains(ExtraFieldLookup):
    def __init__(self, model, field_name):
        super(ExtraFieldLookup, self).__init__(model, field_name,
            'contains', ListField(models.CharField(500), editable=False, null=True))

    def convert_lookup(self, value, annotation):
        return 'startswith', value

    def convert_value(self, value):
        return self.contains_indexer(value)

    @classmethod
    def contains_indexer(cls, value):
        # In indexing mode we add all postfixes ('o', 'lo', ..., 'hello')
        result = []
        if value:
            result.extend([value[count:] for count in range(len(value))])
        return result

class Icontains(Contains):
    def __init__(self, model, field_name):
        super(Contains, self).__init__(model, field_name)
        self.lookup_type = 'icontains'

    def convert_lookup(self, value, annotation):
        return 'startswith', value.lower()

    def convert_value(self, value):
        return [val.lower() for val in super(Contains, self).convert_value(value)]

class Iexact(ExtraFieldLookup):
    def convert_lookup(self, value, annotation):
        return 'exact', value.lower()

    def convert_value(self, value):
        return value.lower()

class Istartswith(ExtraFieldLookup):
    def convert_lookup(self, value, annotation):
        return 'startswith', value.lower()

    def convert_value(self, value):
        return value.lower()

class Endswith(ExtraFieldLookup):
    def convert_lookup(self, value, annotation):
        return 'startswith', value[::-1]

    def convert_value(self, value):
        return value[::-1]

class Iendswith(ExtraFieldLookup):
    def convert_lookup(self, value, annotation):
        return 'startswith', value[::-1].lower()

    def convert_value(self, value):
        return value[::-1].lower()
    