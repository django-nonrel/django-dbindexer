from django.utils.tree import Node
from resolver import resolver

def __repr__(self):
    return '<%s, %s, %s, %s>' % (self.alias, self.col, self.field.name,
        self.field.model.__name__)

from django.db.models.sql.where import Constraint
Constraint.__repr__ = __repr__

# TODO: manipulate a copy of the query instead of the query itself. This has to
# be done because the query can be reused afterwoods by the user so that a
# manipulated query can result in strange behavior for these cases!

class BaseCompiler(object):
    def convert_filters(self, filters):
        model = self.query.model
        for index, child in enumerate(filters.children[:]):
            if isinstance(child, Node):
                self.convert_filters(child)
                continue

            constraint, lookup_type, annotation, value = child
            resolver.convert_filter(self.query, filters, child, index)

class SQLCompiler(BaseCompiler):
    def execute_sql(self, *args, **kwargs):
        self.convert_filters(self.query.where)
        return super(SQLCompiler, self).execute_sql(*args, **kwargs)

    def results_iter(self):
        self.convert_filters(self.query.where)
        return super(SQLCompiler, self).results_iter()


class SQLInsertCompiler(BaseCompiler):
    def execute_sql(self, return_id=False):
        resolver.convert_query(self.query)
        return super(SQLInsertCompiler, self).execute_sql(return_id=return_id)

class SQLUpdateCompiler(BaseCompiler):
    pass

class SQLDeleteCompiler(BaseCompiler):
    pass
