import os.path
from setuptools import setup

import boot


def cat(relpath):
    """Read file contents."""
    with open(os.path.join(os.path.dirname(__file__), relpath)) as f:
        return f.read()


setup(
    name = 'boot.py',
    version = boot.__version__,
    description = 'A dependency graph resolver for program initialization',
    long_description = cat('README.rst'),

    author = boot.__author__,
    author_email = boot.__author_email__,
    license = boot.__license__,
    url = 'https://github.com/clchiou/boot',

    py_modules = ['boot'],
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
