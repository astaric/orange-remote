#!/usr/bin/env python

import os

from setuptools import setup, find_packages

NAME = 'orange-remote'
DOCUMENTATION_NAME = 'Remote Orange'

VERSION = '0.0.1'

DESCRIPTION = 'Addon with server and client that enable remote execution of orange scripts..'
LONG_DESCRIPTION = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()
AUTHOR = 'Anze Staric'
AUTHOR_EMAIL = 'anze.staric@gmail.com'
URL = 'http://github.com/astaric/orange-remote'
DOWNLOAD_URL = 'http://github.com/astaric/orange-remote/download'
LICENSE = 'GPLv3'

KEYWORDS = (
    'orange',
    'orange add-on',
    'visualization'
)

CLASSIFIERS = (
    'Development Status :: 4 - Beta',
    'Environment :: X11 Applications :: Qt',
    'Environment :: Console',
    'Environment :: Plugins',
    'Programming Language :: Python',
    'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    'Operating System :: OS Independent',
    'Topic :: Scientific/Engineering :: Visualization',
    'Topic :: Scientific/Engineering :: Bio-Informatics',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Intended Audience :: Education',
    'Intended Audience :: Science/Research',
    'Intended Audience :: Developers',
)

PACKAGES = find_packages(
    exclude=('*.tests', '*.tests.*', 'tests.*', 'tests'),
)

PACKAGE_DATA = {
}

SETUP_REQUIRES = (
    'setuptools',
)

INSTALL_REQUIRES = (
)

EXTRAS_REQUIRE = {
    'GUI': (
    # Dependencies which are problematic to install automatically
    #'PyQt', # No setup.py
    ),
}

ENTRY_POINTS = {
    'orange.addons': (
        'remote = orangecontrib.remote',
    ),
    'orange.widgets': (
        # This should be unneeded, because module given should load (register)
        # all wanted widgets and prototypes should just have a flag, but for now ...
    ),
}

NAMESPACE_PACAKGES = ["orangecontrib",]

if __name__ == '__main__':
    setup(
        name=NAME,
        version=VERSION,
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        author=AUTHOR,
        author_email=AUTHOR_EMAIL,
        url=URL,
        download_url=DOWNLOAD_URL,
        license=LICENSE,
        keywords=KEYWORDS,
        classifiers=CLASSIFIERS,
        packages=PACKAGES,
        package_data=PACKAGE_DATA,
        setup_requires=SETUP_REQUIRES,
        install_requires=INSTALL_REQUIRES,
        extras_require=EXTRAS_REQUIRE,
        entry_points=ENTRY_POINTS,
        namespace_packages=NAMESPACE_PACAKGES,
        include_package_data=True,
        zip_safe=False,
    )
