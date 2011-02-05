from setuptools import setup, find_packages

DESCRIPTION = 'Expressive NoSQL'
LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.rst').read()
except:
    pass

setup(name='django-dbindexer',
      version='0.3',
      packages=find_packages(),
      author='Waldemar Kornewald, Thomas Wanschik',
      author_email='team@allbuttonspressed.com',
      url='http://www.allbuttonspressed.com/projects/django-dbindexer',
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
          'License :: OSI Approved :: BSD License',
      ],
)
