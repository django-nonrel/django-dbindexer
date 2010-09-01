from django.conf import settings
from django.db import models
from django.utils.importlib import import_module
from djangotoolbox.fields import ListField

import re
regex = type(re.compile(''))

_MODULE_NAMES = getattr(settings, 'DB_INDEX_MODULES', ())

FIELD_INDEXES = {}

def get_index_name(field_name, lookup_type):
    if lookup_type in ('iexact', 'istartswith'):
        index_name = 'idxf_%s_l_%s_%s' % (field_name, lookup_type,
            'case_insensitive')
    elif isinstance(lookup_type, regex) or lookup_type in ('regex', 'iregex'):
        index_name = 'idxf_%s_l_%s' % (field_name, 'regex')
    else:
        index_name = 'idxf_%s_l_%s' % (field_name, lookup_type)

    return index_name

def register_index(model, mapping):
    for name, lookup_types in mapping.items():
        regex_index = False
        if isinstance(lookup_types, basestring):
            lookup_types = (lookup_types,)
        field = model._meta.get_field(name)
        new_lookup_types = list(lookup_types)
        for lookup_type in lookup_types:
            index_name = get_index_name(field.name, lookup_type)
            if lookup_type in ('month', 'day', 'year', 'week_day'):
                index_field = models.IntegerField(editable=False, null=True)
            elif isinstance(lookup_type, regex):
                lookup_type = re.compile(lookup_type.pattern, re.S | re.U |
                    (lookup_type.flags & re.I))
                # add (i)regex lookup type to map for later conversations
                if not lookup_type.flags & re.I and 'regex' not in new_lookup_types:
                    new_lookup_types.append('regex')
                elif lookup_type.flags & re.I and 'iregex' not in new_lookup_types:
                    new_lookup_types.append('iregex')
                # for each indexed field only add one list field shared by all
                # regexes
                if regex_index:
                    continue
                index_field = ListField(models.CharField(
                    max_length=256), editable=False, null=True)
                regex_index = True
            elif lookup_type == 'contains':
                index_field = ListField(models.CharField(
                    max_length=field.max_length), editable=False, null=True)
            else:
                index_field = models.CharField(max_length=field.max_length,
                    editable=False, null=True)
            model.add_to_class(index_name, index_field)
        # set new lookup_types (can be different because of regex lookups)
        FIELD_INDEXES.setdefault(model, {})[name] = new_lookup_types

def load_indexes():
    for name in _MODULE_NAMES:
        try:
            import_module(name)
        except ImportError:
            pass
