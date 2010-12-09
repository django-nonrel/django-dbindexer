from django.db import models, DatabaseError
from django.test import TestCase
from dbindexer.api import register_index
from dbindexer.lookups import StandardLookup
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

register_index(Indexed, {
    'name': ('iexact', 'endswith', 'istartswith', 'iendswith', 'contains',
             'icontains', re.compile('^i+', re.I), re.compile('^I+'),
             re.compile('^i\d*i$', re.I)),
    'published': ('month', 'day', 'year', 'week_day'),
    'tags': ('iexact', 'icontains', StandardLookup(), ),
#    'foreignkey': 'iexact',
    'foreignkey__title': 'iexact',
    'foreignkey__name_fi': 'iexact',
    'foreignkey__fk__name_fi2': 'iexact',
    'foreignkey2__name_fi2': (StandardLookup(), 'iexact', ),
    'foreignkey2__age': (StandardLookup(), )
})

class TestIndexed(TestCase):
    def setUp(self):
        juubi = ForeignIndexed2(name_fi2='Juubi', age=2)
        juubi.save()
        kyuubi = ForeignIndexed(name_fi='Kyuubi', title='Bijuu', fk=juubi)
        kyuubi.save()
        Indexed(name='ItAchi', tags=('Sasuke', 'Madara'), foreignkey=kyuubi,
                foreignkey2=juubi).save()
        Indexed(name='YondAimE', tags=('Naruto', 'Jiraya'), foreignkey=kyuubi,
                foreignkey2=juubi).save()
        Indexed(name='I1038593i', tags=('Sharingan'), foreignkey=kyuubi,
                foreignkey2=juubi).save()

    def test_joins(self):
        self.assertEqual(3, len(Indexed.objects.all().filter(
            foreignkey__fk__name_fi2__iexact='juuBi',
            foreignkey__title__iexact='biJuu')))
        self.assertEqual(3, len(Indexed.objects.all().filter(
            foreignkey__name_fi__iexact='kyuuBi',
            foreignkey__title__iexact='biJuu')))
        self.assertEqual(3, len(Indexed.objects.all().filter(
            foreignkey__title__iexact='biJuu')))
        self.assertEqual(1, len(Indexed.objects.all().filter(
            foreignkey__title__iexact='biJuu', name__iendswith='iMe')))
        self.assertEqual(3, len(Indexed.objects.all().filter(
           foreignkey2__name_fi2='Juubi')))
        
        # test JOINs via different paths targeting the same field
        self.assertEqual(3, len(Indexed.objects.all().filter(
            foreignkey__fk__name_fi2__iexact='juuBi')))
        self.assertEqual(3, len(Indexed.objects.all().filter(
           foreignkey2__name_fi2__iexact='Juubi')))
        
        # test standard lookups for foreign_keys
        self.assertEqual(3, len(Indexed.objects.all().filter(
            foreignkey2__age=2)))
        self.assertEqual(3, len(Indexed.objects.all().filter(
            foreignkey2__age__lt=3)))

    def test_fix_fk_isnull(self):
        self.assertEqual(0, len(Indexed.objects.filter(foreignkey=None)))
        self.assertEqual(3, len(Indexed.objects.exclude(foreignkey=None)))

    def test_iexact(self):
        self.assertEqual(1, len(Indexed.objects.filter(name__iexact='itaChi')))
        self.assertEqual(1, Indexed.objects.filter(name__iexact='itaChi').count())
        
        # test on list field
        self.assertEqual(1, Indexed.objects.filter(tags__iexact='SasuKE').count())
    
    def test_standard_lookups(self):
        self.assertEqual(1, Indexed.objects.filter(tags__exact='Naruto').count())
    
    def test_delete(self):
        Indexed.objects.get(name__iexact='itaChi').delete()
        self.assertEqual(0, Indexed.objects.all().filter(name__iexact='itaChi').count())

    def test_delete_query(self):
        Indexed.objects.all().delete()
        self.assertEqual(0, Indexed.objects.all().filter(name__iexact='itaChi').count())
#
    def test_istartswith(self):
        self.assertEqual(1, len(Indexed.objects.all().filter(name__istartswith='iTa')))

    def test_endswith(self):
        self.assertEqual(1, len(Indexed.objects.all().filter(name__endswith='imE')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__iendswith='iMe')))

    def test_regex(self):
        self.assertEqual(2, len(Indexed.objects.all().filter(name__iregex='^i+')))
        self.assertEqual(2, len(Indexed.objects.all().filter(name__regex='^I+')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__iregex='^i\d*i$')))

    def test_date_filters(self):
        now = datetime.now()
        self.assertEqual(3, len(Indexed.objects.all().filter(published__month=now.month)))
        self.assertEqual(3, len(Indexed.objects.all().filter(published__day=now.day)))
        self.assertEqual(3, len(Indexed.objects.all().filter(published__year=now.year)))
        self.assertEqual(3, len(Indexed.objects.all().filter(
            published__week_day=now.isoweekday())))

#    def test_contains(self):
#        # passes on production but not on gae-sdk (development)
#        self.assertEqual(1, len(Indexed.objects.all().filter(name__contains='Aim')))
#        self.assertEqual(1, len(Indexed.objects.all().filter(name__icontains='aim')))
#
#        # test icontains on a list
#        self.assertEqual(2, len(Indexed.objects.all().filter(tags__icontains='RA')))