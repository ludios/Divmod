from epsilon.setuphelper import autosetup

from clickchronicle import version

autosetup(
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
    )
