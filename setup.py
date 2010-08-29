from setuptools import setup, find_packages

DESCRIPTION = 'Emulate SQL features on NoSQL/non-relational DBs'
LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.rst').read()
except:
    pass

setup(name='django-dbindexer',
      version='0.1',
      packages=find_packages(),
      author='Waldemar Kornewald',
      author_email='wkornewald@gmail.com',
      url='http://www.allbuttonspressed.com/projects/django-dbindexer',
      license='MIT',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      platforms=['any'],
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'Environment :: Web Environment',
          'Framework :: Django',
          'Intended Audience :: Developers',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Software Development :: Libraries :: Application Frameworks',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ],
)
