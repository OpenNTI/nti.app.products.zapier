import codecs
from setuptools import setup
from setuptools import find_packages

entry_points = {
    'console_scripts': [
    ],
    "z3c.autoinclude.plugin": [
        'target = nti.app.products',
    ],
}

TESTS_REQUIRE = [
    'nti.testing',
    'zope.testrunner',
    'fudge',
    'pyhamcrest',
    'nose2[coverage_plugin]',
    'responses',
    'fakeredis',
    'nti.app.testing',
    'nti.app.contenttypes.credit',
    'nti.app.sites.alpha',
    'nti.app.products.ou',
]


def _read(fname):
    with codecs.open(fname, encoding='utf-8') as f:
        return f.read()


setup(
    name='nti.app.products.zapier',
    version='0.0.1.dev0',
    author='Josh Zuech',
    author_email='josh.zuech@nextthought.com',
    description="NTI zapier",
    long_description=(
        _read('README.rst')
        + '\n\n'
        + _read("CHANGES.rst")
    ),
    license='Apache',
    keywords='Products zapier',
    classifiers=[
        'Framework :: Zope3',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    url="https://github.com/NextThought/nti.app.products.zapier",
    zip_safe=False,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    namespace_packages=['nti', 'nti.app', 'nti.app.products'],
    tests_require=TESTS_REQUIRE,
    install_requires=[
        'setuptools',
        'pyramid',
        'requests',
        'nti.app.products.courseware',
        'nti.coremetadata',
        'nti.dataserver',
        'nti.externalization',
        'nti.property',
        'nti.schema',
        'nti.webhooks',
        'zope.cachedescriptors',
        'zope.component',
        'zope.i18nmessageid',
        'zope.interface',
        'zope.lifecycleevent',
        'zope.annotation',
        'zope.schema',
        'zope.security',
        'zope.securitypolicy',
        'zope.traversing',
    ],
    extras_require={
        'test': TESTS_REQUIRE,
        'docs': [
            'Sphinx',
            'repoze.sphinx.autointerface',
            'sphinx_rtd_theme',
            'nti_sphinx_questions'
        ],
    },
    entry_points=entry_points,
)
