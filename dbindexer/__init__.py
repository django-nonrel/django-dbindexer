def autodiscover():
    from autoload import autodiscover as auto_discover
    auto_discover('dbindexes')

def load_indexes():
    from django.conf import settings
    from django.utils.importlib import import_module

    for name in getattr(settings, 'DB_INDEX_MODULES', ()):
        import_module(name)
