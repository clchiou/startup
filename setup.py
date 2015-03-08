from setuptools import setup

import boot

setup(
    name = 'boot',
    version = boot.__version__,
    description = 'A dependency graph resolver for program initialization',
    long_description = boot.__doc__,

    author = boot.__author__,
    author_email = boot.__author_email__,
    license = boot.__license__,
    url = 'https://github.com/clchiou/boot',

    py_modules = ['boot'],
    test_suite = 'boot_test',

    classifiers = [
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
