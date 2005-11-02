from distutils.core import setup

from clickchronicle import version

distobj = setup(
    name="ClickChronicle",
    version=version.short(),
    maintainer="Divmod, Inc.",
    maintainer_email="support@divmod.org",
    url="http://divmod.org/trac/wiki/ClickChronicle",
    license="MIT",
    platforms=["any"],
    description="Record and full-text search your web browsing history.",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: JavaScript",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        ],

    packages=[
        'clickchronicle',
        'clickchronicle.stats',

        'axiom.plugins',
        'xmantissa.plugins'],

    package_data={
        'clickchronicle': [
            'static/clickchronicle.xpi',
            'static/html/*',
            'static/css/*',
            'static/js/*.js',
            'static/js/MochiKit/*.js',
            'static/images/*.png',
            'static/images/screenshots/*.png',
            'themes/cc-base/*',
            ]})

from epsilon.setuphelper import regeneratePluginCache
regeneratePluginCache(distobj)
