from django.db import models
from django.test import TestCase
from .api import register_index
from .lookups import StandardLookup
from .resolver import resolver
from djangotoolbox.fields import ListField
from datetime import datetime
import re

class ForeignIndexed2(models.Model):
    name_fi2 = models.CharField(max_length=500)
    age = models.IntegerField()

class ForeignIndexed(models.Model):
    title = models.CharField(max_length=500)
    name_fi = models.CharField(max_length=500)
    fk = models.ForeignKey(ForeignIndexed2, null=True)

class Indexed(models.Model):
    name = models.CharField(max_length=500)
    published = models.DateTimeField(auto_now_add=True)
    foreignkey = models.ForeignKey(ForeignIndexed, null=True)
    foreignkey2 = models.ForeignKey(ForeignIndexed2, related_name='idx_set', null=True)
    tags = ListField(models.CharField(max_length=500, null=True))

class NullableCharField(models.Model):
    name = models.CharField(max_length=500, null=True)

# TODO: add test for foreign key with multiple filters via different and equal paths
# to do so we have to create some entities matching equal paths but not matching
# different paths
class IndexedTest(TestCase):
    def setUp(self):
        self.backends = list(resolver.backends)
        resolver.backends = []
        resolver.load_backends(('dbindexer.backends.BaseResolver',
                      'dbindexer.backends.FKNullFix',
#                      'dbindexer.backends.InMemoryJOINResolver',
                      'dbindexer.backends.ConstantFieldJOINResolver',
        ))
        self.register_indexex()

        juubi = ForeignIndexed2(name_fi2='Juubi', age=2)
        juubi.save()
        rikudo = ForeignIndexed2(name_fi2='Rikudo', age=200)
        rikudo.save()

        kyuubi = ForeignIndexed(name_fi='Kyuubi', title='Bijuu', fk=juubi)
        hachibi= ForeignIndexed(name_fi='Hachibi', title='Bijuu', fk=rikudo)
        kyuubi.save()
        hachibi.save()

        Indexed(name='ItAchi', tags=('Sasuke', 'Madara'), foreignkey=kyuubi,
                foreignkey2=juubi).save()
        Indexed(name='YondAimE', tags=('Naruto', 'Jiraya'), foreignkey=kyuubi,
                foreignkey2=juubi).save()
        Indexed(name='Neji', tags=('Hinata'), foreignkey=hachibi,
                foreignkey2=juubi).save()
        Indexed(name='I1038593i', tags=('Sharingan'), foreignkey=hachibi,
                foreignkey2=rikudo).save()

    def tearDown(self):
        resolver.backends = self.backends

    def register_indexex(self):
        register_index(Indexed, {
            'name': ('iexact', 'endswith', 'istartswith', 'iendswith', 'contains',
                     'icontains', re.compile('^i+', re.I), re.compile('^I+'),
                     re.compile('^i\d*i$', re.I)),
            'tags': ('iexact', 'icontains', StandardLookup() ),
            'foreignkey__fk': (StandardLookup()),
            'foreignkey__title': 'iexact',
            'foreignkey__name_fi': 'iexact',
            'foreignkey__fk__name_fi2': ('iexact', 'endswith'),
            'foreignkey2__name_fi2': (StandardLookup(), 'iexact'),
            'foreignkey2__age': (StandardLookup())
        })

        register_index(ForeignIndexed, {
            'title': 'iexact',
            'name_fi': ('iexact', 'icontains'),
            'fk__name_fi2': ('iexact', 'endswith'),
            'fk__age': (StandardLookup()),
        })

        register_index(NullableCharField, {
             'name': ('iexact', 'istartswith', 'endswith', 'iendswith',)
        })

    # TODO: add tests for created indexes for all backends!
#    def test_model_fields(self):
#        field_list = [(item[0], item[0].column)
#                       for item in Indexed._meta.get_fields_with_model()]
#        print field_list
#        x()
        # in-memory JOIN backend shouldn't create multiple indexes on the foreignkey side
        # for different paths or not even for index definition on different models. Test this!
        # standard JOIN backend should always add extra fields to registered model. Test this!

    def test_joins(self):
        self.assertEqual(2, len(Indexed.objects.all().filter(
            foreignkey__fk__name_fi2__iexact='juuBi',
            foreignkey__title__iexact='biJuu')))

        self.assertEqual(0, len(Indexed.objects.all().filter(
            foreignkey__fk__name_fi2__iexact='juuBi',
            foreignkey2__name_fi2__iexact='Rikudo')))

        self.assertEqual(1, len(Indexed.objects.all().filter(
            foreignkey__fk__name_fi2__endswith='udo',
            foreignkey2__name_fi2__iexact='Rikudo')))

        self.assertEqual(2, len(Indexed.objects.all().filter(
            foreignkey__title__iexact='biJuu',
            foreignkey__name_fi__iexact='kyuuBi')))

        self.assertEqual(2, len(Indexed.objects.all().filter(
            foreignkey__title__iexact='biJuu',
            foreignkey__name_fi__iexact='Hachibi')))

        self.assertEqual(1, len(Indexed.objects.all().filter(
            foreignkey__title__iexact='biJuu', name__iendswith='iMe')))

        # JOINs on one field only
        self.assertEqual(4, len(Indexed.objects.all().filter(
            foreignkey__title__iexact='biJuu')))
        self.assertEqual(3, len(Indexed.objects.all().filter(
           foreignkey2__name_fi2='Juubi')))

        # text endswith instead iexact all the time :)
        self.assertEqual(2, len(Indexed.objects.all().filter(
            foreignkey__fk__name_fi2__endswith='bi')))

        # test JOINs via different paths targeting the same field
        self.assertEqual(2, len(Indexed.objects.all().filter(
            foreignkey__fk__name_fi2__iexact='juuBi')))
        self.assertEqual(3, len(Indexed.objects.all().filter(
           foreignkey2__name_fi2__iexact='Juubi')))

        # test standard lookups for foreign_keys
        self.assertEqual(3, len(Indexed.objects.all().filter(
            foreignkey2__age=2)))
        self.assertEqual(4, len(Indexed.objects.all().filter(
            foreignkey2__age__lt=201)))

        # test JOINs on different model
        # standard lookups JOINs
        self.assertEqual(1, len(ForeignIndexed.objects.all().filter(
            fk__age=2)))
        self.assertEqual(2, len(ForeignIndexed.objects.all().filter(
            fk__age__lt=210)))

        # other JOINs
        self.assertEqual(1, len(ForeignIndexed.objects.all().filter(
            fk__name_fi2__iexact='juUBI')))
        self.assertEqual(1, len(ForeignIndexed.objects.all().filter(
            fk__name_fi2__endswith='bi')))

    def test_fix_fk_isnull(self):
        self.assertEqual(0, len(Indexed.objects.filter(foreignkey=None)))
        self.assertEqual(4, len(Indexed.objects.exclude(foreignkey=None)))

    def test_iexact(self):
        self.assertEqual(1, len(Indexed.objects.filter(name__iexact='itaChi')))
        self.assertEqual(1, Indexed.objects.filter(name__iexact='itaChi').count())

        self.assertEqual(2, ForeignIndexed.objects.filter(title__iexact='BIJUU').count())
        self.assertEqual(1, ForeignIndexed.objects.filter(name_fi__iexact='KYuubi').count())

        # test on list field
        self.assertEqual(1, Indexed.objects.filter(tags__iexact='SasuKE').count())

    def test_standard_lookups(self):
        self.assertEqual(1, Indexed.objects.filter(tags__exact='Naruto').count())

        # test standard lookup on foreign_key
        juubi = ForeignIndexed2.objects.all().get(name_fi2='Juubi', age=2)
        self.assertEqual(2, Indexed.objects.filter(foreignkey__fk=juubi).count())

    def test_delete(self):
        Indexed.objects.get(name__iexact='itaChi').delete()
        self.assertEqual(0, Indexed.objects.all().filter(name__iexact='itaChi').count())

    def test_delete_query(self):
        Indexed.objects.all().delete()
        self.assertEqual(0, Indexed.objects.all().filter(name__iexact='itaChi').count())

    def test_exists_query(self):
        self.assertTrue(Indexed.objects.filter(name__iexact='itaChi').exists())

    def test_istartswith(self):
        self.assertEqual(1, len(Indexed.objects.all().filter(name__istartswith='iTa')))

    def test_endswith(self):
        self.assertEqual(1, len(Indexed.objects.all().filter(name__endswith='imE')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__iendswith='iMe')))

    def test_regex(self):
        self.assertEqual(2, len(Indexed.objects.all().filter(name__iregex='^i+')))
        self.assertEqual(2, len(Indexed.objects.all().filter(name__regex='^I+')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__iregex='^i\d*i$')))

    def test_null_strings(self):
        """Test indexing with nullable CharFields, see: https://github.com/django-nonrel/django-dbindexer/issues/3."""
        NullableCharField.objects.create()

    def test_contains(self):
        self.assertEqual(1, len(Indexed.objects.all().filter(name__contains='Aim')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__icontains='aim')))

        self.assertEqual(1, ForeignIndexed.objects.filter(name_fi__icontains='Yu').count())

        # test icontains on a list
        self.assertEqual(2, len(Indexed.objects.all().filter(tags__icontains='RA')))


class AutoNowIndexed(models.Model):
    published = models.DateTimeField(auto_now=True)

class AutoNowAddIndexed(models.Model):
    published = models.DateTimeField(auto_now_add=True)

class DateIndexed(models.Model):
    published = models.DateTimeField()

class DateAutoNowTest(TestCase):
    def setUp(self):
        self.backends = list(resolver.backends)
        resolver.backends = []
        resolver.load_backends(('dbindexer.backends.BaseResolver',
                      'dbindexer.backends.FKNullFix',
#                      'dbindexer.backends.InMemoryJOINResolver',
                      'dbindexer.backends.ConstantFieldJOINResolver',
        ))
        self.register_indexex()

        DateIndexed(published=datetime.now()).save()
        DateIndexed(published=datetime.now()).save()
        DateIndexed(published=datetime.now()).save()
        DateIndexed(published=datetime.now()).save()

    def tearDown(self):
        resolver.backends = self.backends

    def register_indexex(self):
        register_index(DateIndexed, {
            'published': ('month', 'day', 'year', 'week_day'),
        })

    def test_auto_now(self):
        from django.core.exceptions import ImproperlyConfigured

        self.assertRaises(ImproperlyConfigured, register_index, AutoNowIndexed, {
            'published': ('month', 'day', 'year', 'week_day'),
        })
        self.assertRaises(ImproperlyConfigured, register_index, AutoNowAddIndexed, {
            'published': ('month', 'day', 'year', 'week_day'),
        })

    def test_date_filters(self):
        now = datetime.now()
        self.assertEqual(4, len(DateIndexed.objects.all().filter(published__month=now.month)))
        self.assertEqual(4, len(DateIndexed.objects.all().filter(published__day=now.day)))
        self.assertEqual(4, len(DateIndexed.objects.all().filter(published__year=now.year)))
        self.assertEqual(4, len(DateIndexed.objects.all().filter(
            published__week_day=now.isoweekday())))
