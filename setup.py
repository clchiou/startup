from setuptools import setup

import startup


setup(
    name = 'startup',
    version = startup.__version__,
    description = 'A dependency graph resolver for program startup',
    long_description = startup.__doc__,

    author = startup.__author__,
    author_email = startup.__author_email__,
    license = startup.__license__,
    url = 'https://github.com/clchiou/startup',

    py_modules = ['startup'],
    test_suite = 'test',

    platforms = '*',
    classifiers = [
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
