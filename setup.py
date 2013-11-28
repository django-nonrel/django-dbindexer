from distutils.core import setup
import os

def get_packages(package):
    return [dirpath
            for dirpath, dirnames, filenames in os.walk(package)
            if os.path.exists(os.path.join(dirpath, '__init__.py'))]


DESCRIPTION = 'Expressive NoSQL for Django'
LONG_DESCRIPTION = None
try:
    LONG_DESCRIPTION = open('README.rst').read()
except:
    pass

setup(name='django-dbindexer',
      version='1.6.0',
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      author='Waldemar Kornewald, Thomas Wanschik',
      author_email='team@allbuttonspressed.com',
      url='https://github.com/django-nonrel/django-dbindexer',
      packages=get_packages('dbindexer'),
      license='3-clause BSD',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Web Environment',
          'Framework :: Django',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.5',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Topic :: Software Development :: Libraries :: Application Frameworks',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ],
)
