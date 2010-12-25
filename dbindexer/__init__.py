def autodiscover():
    """
    Automatically loads database index definitions from db_indexes modules in
    installed apps.
    """
    from django.conf import settings
    from django.utils.importlib import import_module
    from django.utils.module_loading import module_has_submodule

    for app in settings.INSTALLED_APPS:
        mod = import_module(app)
        # Attempt to import the app's admin module.
        try:
            import_module('%s.dbindexes' % app)
        except:
            # Decide whether to bubble up this error. If the app just
            # doesn't have an admin module, we can ignore the error
            # attempting to import it, otherwise we want it to bubble up.
            if module_has_submodule(mod, 'dbindexes'):
                raise

def load_indexes():
    from django.conf import settings
    from django.utils.importlib import import_module

    for name in getattr(settings, 'DB_INDEX_MODULES', ()):
        import_module(name)
