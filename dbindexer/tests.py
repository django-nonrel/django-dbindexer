# -*- coding: utf-8 -*-
from django.db import models
from django.test import TestCase
from datetime import datetime

class Indexed(models.Model):
    name = models.CharField(max_length=500)
    published = models.DateTimeField(auto_now_add=True)

from dbindexer.api import register_index

register_index(Indexed, {
    'name': ('iexact', 'endswith', 'istartswith', 'iendswith', 'contains',
        'icontains'),
    'published': ('month', 'day', 'week_day'),
})

class TestIndexed(TestCase):
    def setUp(self):
        Indexed(name='ItAchi').save()
        Indexed(name='YondAimE').save()

    def test_setup(self):
        now = datetime.now()
        self.assertEqual(1, len(Indexed.objects.all().filter(name__iexact='itachi')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__istartswith='ita')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__endswith='imE')))
        self.assertEqual(1, len(Indexed.objects.all().filter(name__iendswith='ime')))
        self.assertEqual(2, len(Indexed.objects.all().filter(name__contains='A')))
        self.assertEqual(2, len(Indexed.objects.all().filter(name__icontains='a')))

        # passes on production but not on sdk (development)
#        self.assertEqual(1, len(Indexed.objects.all().filter(name__contains='Aim')))
#        self.assertEqual(1, len(Indexed.objects.all().filter(name__icontains='aim')))

        self.assertEqual(2, len(Indexed.objects.all().filter(published__month=now.month)))
        self.assertEqual(2, len(Indexed.objects.all().filter(published__day=now.day)))
        self.assertEqual(2, len(Indexed.objects.all().filter(
            published__week_day=now.isoweekday())))
