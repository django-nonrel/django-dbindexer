from django.conf import settings
from django.utils.importlib import import_module


def merge_dicts(d1, d2):
    '''Update dictionary recursively. If values for a given key exist in both dictionaries and are dict-like they are merged.'''

    for k, v in d2.iteritems():

        # Try to merge the values as if they were dicts.
        try:
            merge_dicts(d1[k], v)

        # Otherwise just overwrite the original value (if any).
        except (AttributeError, KeyError):
            d1[k] = v


class DatabaseOperations(object):
    dbindexer_compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'

    def __init__(self):
        self._dbindexer_cache = {}

    def compiler(self, compiler_name):
        if compiler_name not in self._dbindexer_cache:
            target = super(DatabaseOperations, self).compiler(compiler_name)
            base = getattr(
                import_module(self.dbindexer_compiler_module), compiler_name)
            class Compiler(base, target):
                pass
            self._dbindexer_cache[compiler_name] = Compiler
        return self._dbindexer_cache[compiler_name]

class BaseDatabaseWrapper(object):
    def __init__(self, *args, **kwargs):
        super(BaseDatabaseWrapper, self).__init__(*args, **kwargs)
        class Operations(DatabaseOperations, self.ops.__class__):
            pass
        self.ops.__class__ = Operations
        self.ops.__init__()

def DatabaseWrapper(settings_dict, *args, **kwargs):
    target_settings = settings_dict['TARGET']
    if isinstance(target_settings, (str, unicode)):
        target_settings = settings.DATABASES[target_settings]
    engine = target_settings['ENGINE'] + '.base'
    target = import_module(engine).DatabaseWrapper
    class Wrapper(BaseDatabaseWrapper, target):
        pass

    # Update settings with target database settings (which can contain nested dicts).
    merged_settings = settings_dict.copy()
    merge_dicts(merged_settings, target_settings)

    return Wrapper(merged_settings, *args, **kwargs)
