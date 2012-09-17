Django-dbindexer, emulate SQL features on NoSQL databases
=========================================================

Documentation at http://django-dbindexer.readthedocs.org/

With django-dbindexer_ you can emulate SQL features on NoSQL databases. For example, if your database doesn't support case-insensitive queries (iexact, istartswith, etc.) you can just tell the indexer which models and fields should support these queries and it'll take care of maintaining the required indexes for you. Magically, the previously unsupported queries will just work. Currently, this project is in a very early development stage. The long-term plan is to support JOINs and at least some simple aggregates, possibly even much more.

Contributing
------------
You are highly encouraged to participate in the development, simply use
GitHub's fork/pull request system.

If you don't like GitHub (for some reason) you're welcome
to send regular patches to the mailing list.

:Mailing list: http://groups.google.com/group/django-non-relational
:Bug tracker: https://github.com/django-nonrel/django-dbindexer/issues
:License: 3-clause BSD, see LICENSE
:Keywords: django, app engine, mongodb, orm, nosql, database, python
