With django-dbindexer_ you can emulate SQL features on NoSQL databases. For example, if your database doesn't support case-insensitive queries (iexact, istartswith, etc.) you can just tell the indexer which models and fields should support these queries and it'll take care of maintaining the required indexes for you. Magically, the previously unsupported queries will just work. Currently, this project is in a very early development stage. The long-term plan is to support JOINs and at least some simple aggregates, possibly even much more.

Visit the `project site`_ for more information.

.. _django-dbindexer: http://www.allbuttonspressed.com/projects/django-dbindexer
.. _project site: django-dbindexer_
