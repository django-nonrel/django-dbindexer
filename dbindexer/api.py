from .lookups import LookupDoesNotExist, ExtraFieldLookup
from . import lookups as lookups_module
from .resolver import resolver
import inspect

# TODO: add possibility to add lookup modules
def create_lookup(lookup_def):
    for _, cls in inspect.getmembers(lookups_module):
        if inspect.isclass(cls) and issubclass(cls, ExtraFieldLookup) and \
                cls.matches_lookup_def(lookup_def):
            return cls()
    raise LookupDoesNotExist('No Lookup found for %s .' % lookup_def)

def register_index(model, mapping):
    for field_name, lookups in mapping.items():
        if not isinstance(lookups, (list, tuple)):
            lookups = (lookups, )

        # create indexes and add model and field_name to lookups
        # create ExtraFieldLookup instances on the fly if needed
        for lookup in lookups:
            lookup_def = None
            if not isinstance(lookup, ExtraFieldLookup):
                lookup_def = lookup
                lookup = create_lookup(lookup_def)
            lookup.contribute(model, field_name, lookup_def)
            resolver.create_index(lookup)
