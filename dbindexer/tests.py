from dbindexer.api import register_index
from django.db import models
from django.test import TestCase
from datetime import datetime
import re

class ForeignIndexed(models.Model):
    title = models.CharField(max_length=500)
    name = models.CharField(max_length=500)

class ForeignIndexed2(models.Model):
    name = models.CharField(max_length=500)

class Indexed(models.Model):
    name = models.CharField(max_length=500)
    published = models.DateTimeField(auto_now_add=True)
    foreignkey = models.ForeignKey(ForeignIndexed)
    foreignkey2 = models.ForeignKey(ForeignIndexed2, related_name='idx_set')

register_index(Indexed, {
    'name': ('iexact', 'endswith', 'istartswith', 'iendswith', 'contains',
        'icontains', re.compile('^i+', re.I), re.compile('^I+'),
        re.compile('^i\d*i$', re.I)),
    'published': ('month', 'day', 'week_day'),
    'foreignkey': 'iexact',
    'foreignkey__title': 'iexact',
    'foreignkey__name': 'iexact',
    'foreignkey2__name': '$default'
})

class TestIndexed(TestCase):
    def setUp(self):
        kyuubi = ForeignIndexed(name='Kyuubi', title='Bijuu')
        juubi = ForeignIndexed2(name='Juubi')
        kyuubi.save()
        juubi.save()
        Indexed(name='ItAchi', foreignkey=kyuubi, foreignkey2=juubi).save()
        Indexed(name='YondAimE', foreignkey=kyuubi, foreignkey2=juubi).save()
        Indexed(name='I1038593i', foreignkey=kyuubi, foreignkey2=juubi).save()

    def test_setup(self):
        now = datetime.now()
        self.assertEqual(1, len(Indexed.objects.all().filter(name__iexact='itachi')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__istartswith='ita')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__endswith='imE')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__iendswith='ime')))
        self.assertEqual(2, len(Indexed.objects.all().filter(name__iregex='^i+')))
        self.assertEqual(2, len(Indexed.objects.all().filter(name__regex='^I+')))
        self.assertEqual(0, len(Indexed.objects.all().filter(name__regex='^i+')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__iregex='^i\d*i$')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__iexact='itachi')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__istartswith='ita')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__endswith='imE')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__iendswith='ime')))
        self.assertEqual(2, len(Indexed.objects.all().filter(name__iregex='^i+')))
        self.assertEqual(2, len(Indexed.objects.all().filter(name__regex='^I+')))
        self.assertEqual(0, len(Indexed.objects.all().filter(name__regex='^i+')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__iregex='^i\d*i$')))

        # passes on production but not on sdk (development)
#        self.assertEqual(1, len(Indexed.objects.all().filter(name__contains='Aim')))
#        self.assertEqual(1, len(Indexed.objects.all().filter(name__icontains='aim')))

        self.assertEqual(3, len(Indexed.objects.all().filter(published__month=now.month)))
        self.assertEqual(3, len(Indexed.objects.all().filter(published__day=now.day)))
        self.assertEqual(3, len(Indexed.objects.all().filter(
            published__week_day=now.isoweekday())))
